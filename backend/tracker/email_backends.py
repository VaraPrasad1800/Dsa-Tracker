"""
Production-ready SendGrid email backend for Django.

Uses the official `sendgrid` Python SDK (>=3.6.5). Falls back to Django's
console backend when no SENDGRID_API_KEY is configured so local dev and tests
work without credentials.
"""
import logging
from django.conf import settings
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.core.mail.message import sanitize_address

logger = logging.getLogger(__name__)


class SendGridBackend:
    """
    Django email backend that sends via SendGrid's Web API v3.

    Configure in settings:
        EMAIL_BACKEND = 'tracker.email_backends.SendGridBackend'
        SENDGRID_API_KEY = 'SG.xxx'   # or env var
        DEFAULT_FROM_EMAIL = 'DSA Tracker <no-reply@dsatracker.app>'
    """

    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'DSA Tracker <no-reply@dsatracker.app>')
        # If no API key, delegate to console backend for local dev/tests
        if not self.api_key:
            self._fallback = ConsoleEmailBackend(fail_silently=fail_silently)
        else:
            self._fallback = None
            # Lazy import to avoid import-time dependency when key is absent
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, Content
            self._sg = SendGridAPIClient(self.api_key)
            self._Mail = Mail
            self._Email = Email
            self._Content = Content

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects.

        Returns the number of successfully sent messages.
        """
        if not email_messages:
            return 0

        if self._fallback is not None:
            # No SendGrid key → delegate to console
            return self._fallback.send_messages(email_messages)

        sent_count = 0
        for message in email_messages:
            try:
                self._send_single(message)
                sent_count += 1
            except Exception as e:
                logger.exception('Failed to send email to %s: %s', message.to, e)
                if not self.fail_silently:
                    raise
        return sent_count

    def _send_single(self, message):
        # Build recipient list
        to_emails = [sanitize_address(addr, message.encoding) for addr in message.to]
        cc_emails = [sanitize_address(addr, message.encoding) for addr in message.cc] if message.cc else []
        bcc_emails = [sanitize_address(addr, message.encoding) for addr in message.bcc] if message.bcc else []

        # Build SendGrid Mail object
        # SendGrid 3.6.5 Mail(from_email, subject, to_email, content)
        mail_obj = self._Mail(
            from_email=self._Email(message.from_email or self.from_email),
            subject=message.subject,
            to_email=self._Email(to_emails[0]) if to_emails else None,
            content=self._Content('text/plain', message.body),
        )

        # Add CC / BCC if present
        for addr in cc_emails:
            mail_obj.add_cc(self._Email(addr))
        for addr in bcc_emails:
            mail_obj.add_bcc(self._Email(addr))

        # Add HTML alternative if present
        for alt_content, alt_type in getattr(message, 'alternatives', []):
            if alt_type == 'text/html':
                mail_obj.add_content(self._Content('text/html', alt_content))
                break

        # Send via SendGrid API
        response = self._sg.client.mail.send.post(request_body=mail_obj.get())
        if response.status_code >= 400:
            raise RuntimeError(f'SendGrid API error {response.status_code}: {response.body}')
        logger.info('Sent email "%s" to %s via SendGrid (status %s)', message.subject, to_emails, response.status_code)