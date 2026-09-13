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


    def test_click_tracking_disabled_for_transactional_email(self):
        backend = self._make_backend()
        message = EmailMessage(
            subject='Verify your email',
            body='Click here',
            to=['carol@example.com'],
            from_email='no-reply@dsatracker.app',
        )
        message.disable_click_tracking = True
        backend.send_messages([message])

        request_body = backend._mock_client.client.mail.send.post.call_args.kwargs['request_body']
        self.assertIn('tracking_settings', request_body)
        self.assertEqual(
            request_body['tracking_settings'],
            {'click_tracking': {'enable': False, 'enable_text': False}}
        )

    def test_click_tracking_not_disabled_for_unrelated_email(self):
        backend = self._make_backend()
        message = EmailMessage(
            subject='Weekly update',
            body='Hello',
            to=['carol@example.com'],
            from_email='no-reply@dsatracker.app',
        )
        backend.send_messages([message])

        request_body = backend._mock_client.client.mail.send.post.call_args.kwargs['request_body']
        self.assertNotIn('tracking_settings', request_body)


class VerificationUrlFormatTests(SimpleTestCase):
    """Verifies that verification and reset URLs do not include an unnecessary trailing slash before query params."""

    @patch('tracker.services.email_service._deliver')
    def test_verification_url_has_no_trailing_slash(self, mock_deliver):
        from tracker.services.email_service import send_verification_email
        from unittest.mock import MagicMock

        user = MagicMock()
        user.username = 'testuser'
        user.email = 'test@example.com'

        send_verification_email(user, 'dummytoken123')
        self.assertTrue(mock_deliver.called)
        context = mock_deliver.call_args.kwargs['context']
        link = context['verification_link']
        self.assertIn('/verify-email?token=dummytoken123', link)
        self.assertNotIn('/verify-email/?token=', link)
        # Also verify disable_click_tracking was passed as True
        self.assertTrue(mock_deliver.call_args.kwargs.get('disable_click_tracking'))


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


class VerifyEmailViewRegressionTests(SimpleTestCase):
    """Tests for VerifyEmailView covering success, already_used, expired, invalid, and resend invalidation."""

    def setUp(self):
        from rest_framework.test import APIRequestFactory
        self.factory = APIRequestFactory()

    @patch('tracker.views.UserProfile.objects.select_related')
    def test_successful_verification(self, mock_select_related):
        from tracker.views import VerifyEmailView
        from tracker.services.auth_tokens import hash_token
        from unittest.mock import MagicMock
        from django.utils import timezone

        raw_token = 'fresh_valid_token_123'
        token_hash = hash_token(raw_token)

        mock_profile = MagicMock()
        mock_profile.is_email_verified = False
        mock_profile.email_verification_token_hash = token_hash
        mock_profile.email_verification_sent_at = timezone.now()
        mock_profile.user.id = 1
        mock_profile.user.username = 'alice'
        mock_profile.user.email = 'alice@example.com'

        mock_select_related.return_value.get.return_value = mock_profile

        request = self.factory.post('/api/auth/verify-email/', {'token': raw_token}, format='json')
        response = VerifyEmailView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Email verified successfully. You can now log in.')
        self.assertTrue(mock_profile.is_email_verified)
        mock_profile.save.assert_called_once_with(update_fields=['is_email_verified'])

    @patch('tracker.views.UserProfile.objects.select_related')
    def test_duplicate_verification_returns_already_used(self, mock_select_related):
        from tracker.views import VerifyEmailView
        from tracker.services.auth_tokens import hash_token
        from unittest.mock import MagicMock

        raw_token = 'already_used_token_123'
        token_hash = hash_token(raw_token)

        mock_profile = MagicMock()
        mock_profile.is_email_verified = True  # already verified
        mock_profile.email_verification_token_hash = token_hash

        mock_select_related.return_value.get.return_value = mock_profile

        request = self.factory.post('/api/auth/verify-email/', {'token': raw_token}, format='json')
        response = VerifyEmailView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('code'), 'already_used')
        self.assertIn('already been used', response.data['error'])

    @patch('tracker.views.UserProfile.objects.select_related')
    def test_invalid_token_returns_400(self, mock_select_related):
        from tracker.views import VerifyEmailView
        from tracker.models import UserProfile

        mock_select_related.return_value.get.side_effect = UserProfile.DoesNotExist

        request = self.factory.post('/api/auth/verify-email/', {'token': 'completely_invalid'}, format='json')
        response = VerifyEmailView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Invalid or expired verification token.')

    @patch('tracker.views.UserProfile.objects.select_related')
    def test_expired_token_returns_400_with_code_expired(self, mock_select_related):
        from datetime import timedelta
        from django.utils import timezone
        from tracker.views import VerifyEmailView
        from tracker.services.auth_tokens import hash_token
        from unittest.mock import MagicMock

        raw_token = 'expired_token_123'
        token_hash = hash_token(raw_token)

        mock_profile = MagicMock()
        mock_profile.is_email_verified = False
        mock_profile.email_verification_token_hash = token_hash
        mock_profile.email_verification_sent_at = timezone.now() - timedelta(hours=48)

        mock_select_related.return_value.get.return_value = mock_profile

        request = self.factory.post('/api/auth/verify-email/', {'token': raw_token}, format='json')
        response = VerifyEmailView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('code'), 'expired')
        self.assertIn('Verification link expired', response.data['error'])

    @patch('tracker.views.UserProfile.objects.select_related')
    def test_resend_invalidates_old_token_and_new_token_works(self, mock_select_related):
        from django.utils import timezone
        from tracker.views import VerifyEmailView
        from tracker.services.auth_tokens import hash_token
        from tracker.models import UserProfile
        from unittest.mock import MagicMock

        old_token = 'old_token_123'
        new_token = 'new_token_456'
        new_token_hash = hash_token(new_token)

        mock_profile = MagicMock()
        mock_profile.is_email_verified = False
        mock_profile.email_verification_token_hash = new_token_hash
        mock_profile.email_verification_sent_at = timezone.now()
        mock_profile.user.id = 1
        mock_profile.user.username = 'bob'
        mock_profile.user.email = 'bob@example.com'

        def mock_get(email_verification_token_hash):
            if email_verification_token_hash == new_token_hash:
                return mock_profile
            raise UserProfile.DoesNotExist

        mock_select_related.return_value.get.side_effect = mock_get

        # 1. Old token fails with Invalid or expired
        req_old = self.factory.post('/api/auth/verify-email/', {'token': old_token}, format='json')
        res_old = VerifyEmailView.as_view()(req_old)
        self.assertEqual(res_old.status_code, 400)
        self.assertEqual(res_old.data['error'], 'Invalid or expired verification token.')

        # 2. New token succeeds with 200 OK
        req_new = self.factory.post('/api/auth/verify-email/', {'token': new_token}, format='json')
        res_new = VerifyEmailView.as_view()(req_new)
        self.assertEqual(res_new.status_code, 200)
        self.assertEqual(res_new.data['message'], 'Email verified successfully. You can now log in.')