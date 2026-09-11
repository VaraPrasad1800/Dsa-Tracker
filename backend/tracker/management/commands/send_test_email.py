"""
Django management command to send a real auth email (verification or password reset)
via the currently configured EMAIL_BACKEND.

Useful for realistic SendGrid delivery testing and for local dev where the console
backend prints the link containing the single-use token.

Examples:
    python manage.py send_test_email you@example.com
    python manage.py send_test_email you@example.com --type reset
    python manage.py send_test_email you@example.com --type verification
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from tracker.models import UserProfile
from tracker.services.auth_tokens import create_verification_token, create_password_reset_token
from tracker.services.email_service import send_verification_email, send_password_reset_email

User = get_user_model()


class Command(BaseCommand):
    help = 'Send a test verification or password-reset email via the configured email backend.'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Recipient email address.')
        parser.add_argument(
            '--type',
            type=str,
            choices=['verification', 'reset'],
            default='verification',
            help="Which email to send: 'verification' (default) or 'reset'.",
        )
        parser.add_argument(
            '--username',
            type=str,
            default='dsa_test_user',
            help='Username to use if no matching account exists (for verification emails).',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        email_type = options['type']

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            if email_type == 'verification':
                # Create (or reuse) an account so the token is real and single-use.
                user, created = User.objects.get_or_create(
                    username=options['username'],
                    defaults={'email': email},
                )
                if created:
                    UserProfile.objects.get_or_create(user=user)
                    self.stdout.write(self.style.SUCCESS(f'Created account {user.username} for {email}.'))
            else:
                raise CommandError(
                    f'No account exists for {email}. Password reset requires an existing account.'
                    ' Create one or use --type verification.'
                )

        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            profile = UserProfile.objects.create(user=user)

        if email_type == 'verification':
            token = create_verification_token(profile)
            sent = send_verification_email(user, token)
        else:
            token = create_password_reset_token(profile)
            sent = send_password_reset_email(user, token)

        if sent:
            self.stdout.write(self.style.SUCCESS(
                f'[SendGrid] {email_type} email sent to {email} (backend: {self._backend_name()}).'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Email NOT sent/delivered (send_mail returned 0). Check SENDGRID_API_KEY / logs.'
            ))

    def _backend_name(self):
        from django.conf import settings
        return getattr(settings, 'EMAIL_BACKEND', 'unknown')