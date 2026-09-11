"""Tests for the SendGrid email backend and its console fallback."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.core.mail import EmailMessage, EmailMultiAlternatives

from tracker.email_backends import SendGridBackend


class SendGridBackendFallbackTests(TestCase):
    """Without a SENDGRID_API_KEY the backend delegates to the console backend."""

    @override_settings(SENDGRID_API_KEY='', EMAIL_BACKEND='tracker.email_backends.SendGridBackend')
    def test_falls_back_to_console_without_key(self):
        backend = SendGridBackend(fail_silently=False)
        # Delegates to console backend → no exception, prints to stdout
        message = EmailMessage(
            subject='Hello',
            body='Body',
            from_email='test@example.com',
            to=['someone@example.com'],
        )
        # send via the console delegation path
        sent = backend.send_messages([message])
        self.assertEqual(sent, 1)


@override_settings(
    SENDGRID_API_KEY='SG.testkey',
    EMAIL_BACKEND='tracker.email_backends.SendGridBackend',
    DEFAULT_FROM_EMAIL='DSA Tracker <no-reply@dsatracker.app>',
)
class SendGridBackendClientTests(TestCase):
    """Verifies the SendGrid payload construction without a real network call."""

    def _make_backend(self):
        # Patch the SDK client constructor so we never hit the network
        with patch('sendgrid.SendGridAPIClient') as mock_client_cls:
            backend = SendGridBackend(fail_silently=True)
            mock_client = mock_client_cls.return_value
            # Mock the send endpoint chain
            mock_response = mock_client.client.mail.send.post.return_value
            mock_response.status_code = 202
            mock_response.body = 'accepted'
            backend._mock_client = mock_client
        return backend

    def test_builds_html_content_and_sends(self):
        backend = self._make_backend()
        message = EmailMultiAlternatives(
            subject='Verify your DSA Tracker account',
            body='Plain text body',
            from_email='DSA Tracker <no-reply@dsatracker.app>',
            to=['carol@example.com'],
        )
        message.attach_alternative('<p>Html body</p>', 'text/html')

        sent = backend.send_messages([message])

        self.assertEqual(sent, 1)
        # Verify the payload passed to the SDK contains our content
        request_body = backend._mock_client.client.mail.send.post.call_args.kwargs['request_body']
        # The SendGrid Mail payload is a dict with 'content' listing text/html + text/plain
        self.assertIsInstance(request_body, dict)
        contents = request_body.get('content', [])
        mime_types = {c['type'] for c in contents}
        self.assertIn('text/plain', mime_types)
        self.assertIn('text/html', mime_types)

    def test_sendgrid_http_error_is_surfaceable(self):
        with patch('sendgrid.SendGridAPIClient') as mock_client_cls:
            backend = SendGridBackend(fail_silently=True)
            mock_client = mock_client_cls.return_value
            mock_response = mock_client.client.mail.send.post.return_value
            mock_response.status_code = 500
            mock_response.body = 'boom'

            message = EmailMessage(
                subject='Hello', body='Body',
                to=['carol@example.com'],
                from_email='no-reply@dsatracker.app',
            )
            # fail_silently=True → returns 0, no exception
            sent = backend.send_messages([message])
            self.assertEqual(sent, 0)