"""
Email delivery service for DSA Tracker.

Uses SendGrid in production (tracker.email_backends.SendGridBackend wrapping
the official `sendgrid` SDK) and falls back to Django's console backend when
no SENDGRID_API_KEY is configured, so local development and tests work
without credentials.
"""
import logging

from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

EMAIL_SUBJECTS = {
    'verification': 'Verify your DSA Tracker account',
    'password_reset': 'Reset your password',
}


def _frontend_url():
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')


def _deliver(subject, recipient_email, template_name, context, html_message=None, text_message=None):
    """Deliver an email using the configured backend (SendGrid or console/SMTP)."""
    recipient = recipient_email or ''
    html = html_message or render_to_string(template_name, context)
    text = text_message or f'{subject}\n\nPlease open this message in an HTML-capable client.'

    backend_name = getattr(settings, 'EMAIL_BACKEND', 'unknown')
    logger.info("[EMAIL DEBUG] email service called: subject=%r, recipient=%r", subject, recipient)
    logger.info("[EMAIL DEBUG] backend selected: %s", backend_name)

    try:
        sent = mail.send_mail(
            subject=subject,
            message=text,
            html_message=html,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@dsatracker.com'),
            recipient_list=[recipient],
            fail_silently=False,
        )
        if sent:
            logger.info('[EMAIL DEBUG] mail.send_mail succeeded (sent=%d) to %s', sent, recipient)
        else:
            logger.warning('[EMAIL DEBUG] mail.send_mail returned 0 for %s; check backend configuration.', recipient)
        return sent
    except Exception as exc:
        logger.error('[EMAIL DEBUG] SendGrid/mail send exception for "%s" to %s: %s', subject, recipient, exc, exc_info=True)
        return 0


def send_verification_email(user, token):
    """Send email verification link to a newly registered user."""
    verification_link = f"{_frontend_url()}/verify-email/?token={token}"
    context = {
        'username': user.username,
        'verification_link': verification_link,
        'expiry_hours': getattr(settings, 'EMAIL_VERIFICATION_EXPIRY_HOURS', 24),
    }
    return _deliver(
        subject=EMAIL_SUBJECTS['verification'],
        recipient_email=user.email,
        template_name='emails/signup_verification.html',
        context=context,
        text_message=f'Verify your DSA Tracker account: {verification_link}',
    )


def send_password_reset_email(user, token):
    """Send password reset link to a user who requested one."""
    reset_link = f"{_frontend_url()}/reset-password/?token={token}"
    context = {
        'username': user.username,
        'reset_link': reset_link,
        'expiry_hours': getattr(settings, 'PASSWORD_RESET_EXPIRY_HOURS', 24),
    }
    return _deliver(
        subject=EMAIL_SUBJECTS['password_reset'],
        recipient_email=user.email,
        template_name='emails/password_reset.html',
        context=context,
        text_message=f'Reset your DSA Tracker password: {reset_link}',
    )