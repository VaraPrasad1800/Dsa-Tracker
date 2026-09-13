"""Tests for the SendGrid email backend and its console fallback."""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, EmailMultiAlternatives

from tracker.email_backends import SendGridBackend


class SendGridBackendFallbackTests(SimpleTestCase):
    """Verifies fallback in dev mode and fail-fast in production mode."""

    @override_settings(SENDGRID_API_KEY='', EMAIL_BACKEND='tracker.email_backends.SendGridBackend', DEBUG=True)
    def test_falls_back_to_console_in_debug_mode(self):
        backend = SendGridBackend(fail_silently=False)
        message = EmailMessage(
            subject='Hello',
            body='Body',
            from_email='test@example.com',
            to=['someone@example.com'],
        )
        sent = backend.send_messages([message])
        self.assertEqual(sent, 1)

    @override_settings(SENDGRID_API_KEY='', EMAIL_BACKEND='tracker.email_backends.SendGridBackend', DEBUG=False)
    def test_raises_improperly_configured_in_production_mode(self):
        with self.assertRaises(ImproperlyConfigured):
            SendGridBackend(fail_silently=False)


@override_settings(
    SENDGRID_API_KEY='SG.testkey',
    EMAIL_BACKEND='tracker.email_backends.SendGridBackend',
    DEFAULT_FROM_EMAIL='DSA Tracker <no-reply@dsatracker.app>',
)
class SendGridBackendClientTests(SimpleTestCase):
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


class ResendVerificationViewStatusTests(SimpleTestCase):
    """Verifies that ResendVerificationView accurately reflects email delivery success/failure."""

    @patch('tracker.views.User.objects.get')
    @patch('tracker.views.get_or_create_profile')
    @patch('tracker.views.send_verification_email')
    def test_resend_verification_failure_returns_502(self, mock_send, mock_profile, mock_user_get):
        from rest_framework.test import APIRequestFactory
        from tracker.views import ResendVerificationView

        mock_user = mock_user_get.return_value
        profile = mock_profile.return_value
        profile.is_email_verified = False
        mock_send.return_value = 0  # failure

        factory = APIRequestFactory()
        request = factory.post('/api/auth/resend-verification/', {'email': 'test@example.com'}, format='json')
        view = ResendVerificationView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.data['verification_email_sent'])
        self.assertIn('Failed to send verification email', response.data['error'])

    @patch('tracker.views.User.objects.get')
    @patch('tracker.views.get_or_create_profile')
    @patch('tracker.views.send_verification_email')
    def test_resend_verification_success_returns_200(self, mock_send, mock_profile, mock_user_get):
        from rest_framework.test import APIRequestFactory
        from tracker.views import ResendVerificationView

        mock_user = mock_user_get.return_value
        profile = mock_profile.return_value
        profile.is_email_verified = False
        mock_send.return_value = 1  # success

        factory = APIRequestFactory()
        request = factory.post('/api/auth/resend-verification/', {'email': 'test@example.com'}, format='json')
        view = ResendVerificationView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['verification_email_sent'])