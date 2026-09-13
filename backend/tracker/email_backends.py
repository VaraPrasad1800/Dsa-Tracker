"""
Production-ready SendGrid email backend for Django.

Uses the official `sendgrid` Python SDK (v6+).
In development (DEBUG=True), falls back to Django's console backend when
no SENDGRID_API_KEY is configured so local dev and tests work without credentials.
In production (DEBUG=False), raises ImproperlyConfigured if SENDGRID_API_KEY is
missing, failing clearly instead of pretending emails were delivered.
"""
import email.utils
import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.core.mail.message import sanitize_address

logger = logging.getLogger(__name__)


class SendGridBackend(BaseEmailBackend):
    """
    Django email backend that sends via SendGrid's Web API v3 using the modern SDK.

    Configure in settings:
        EMAIL_BACKEND = 'tracker.email_backends.SendGridBackend'
        SENDGRID_API_KEY = 'SG.xxx'   # or env var
        DEFAULT_FROM_EMAIL = 'DSA Tracker <no-reply@dsatracker.app>'
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = (getattr(settings, 'SENDGRID_API_KEY', '') or '').strip()
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'DSA Tracker <no-reply@dsatracker.app>')

        is_debug = getattr(settings, 'DEBUG', True)
        if not self.api_key:
            if not is_debug:
                logger.error("[EMAIL DEBUG] SendGrid API key configured: false (in production)")
                raise ImproperlyConfigured(
                    "SENDGRID_API_KEY is missing or empty. "
                    "Cannot send emails in production without a configured SendGrid API key."
                )
            logger.info("[EMAIL DEBUG] SendGrid API key configured: false (dev fallback to console)")
            self._fallback = ConsoleEmailBackend(fail_silently=fail_silently)
        else:
            self._fallback = None
            logger.info(
                "[EMAIL DEBUG] SendGrid backend initialized (configured=true, key_length=%d, from_email=%r)",
                len(self.api_key),
                self.from_email,
            )
            # Lazy import to avoid import-time dependency when key is absent
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, Cc, Bcc
            self._sg = SendGridAPIClient(self.api_key)
            self._Mail = Mail
            self._Email = Email
            self._Cc = Cc
            self._Bcc = Bcc

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects.

        Returns the number of successfully sent messages.
        """
        if not email_messages:
            return 0

        if self._fallback is not None:
            logger.info("[EMAIL DEBUG] Delegating to console backend fallback")
            return self._fallback.send_messages(email_messages)

        sent_count = 0
        for message in email_messages:
            try:
                self._send_single(message)
                sent_count += 1
            except Exception as e:
                logger.exception('[EMAIL DEBUG] Failed to send email to %s: %s', message.to, e)
                if not self.fail_silently:
                    raise
        return sent_count

    def _send_single(self, message):
        # 1. Sanitize recipient list
        to_emails = [sanitize_address(addr, message.encoding) for addr in message.to]
        if not to_emails:
            logger.warning('[EMAIL DEBUG] Email message has no recipients; skipping.')
            return

        logger.info("[EMAIL DEBUG] SendGrid backend invoked for subject=%r to=%r", message.subject, to_emails)

        # 2. Parse from_email into display name and clean address for SendGrid v3
        raw_from = message.from_email or self.from_email
        name, addr = email.utils.parseaddr(raw_from)
        if name:
            from_email_obj = self._Email(addr, name)
        else:
            from_email_obj = self._Email(addr or raw_from)

        # 3. Extract HTML alternative if present
        html_content = None
        for alt_content, alt_type in getattr(message, 'alternatives', []):
            if alt_type == 'text/html':
                html_content = alt_content
                break

        # 4. Build modern SendGrid v6 Mail object
        mail_obj = self._Mail(
            from_email=from_email_obj,
            to_emails=to_emails,
            subject=message.subject,
            plain_text_content=message.body,
            html_content=html_content,
        )

        # 5. Add CC / BCC if present
        if message.cc:
            for addr in message.cc:
                mail_obj.add_cc(self._Cc(sanitize_address(addr, message.encoding)))
        if message.bcc:
            for addr in message.bcc:
                mail_obj.add_bcc(self._Bcc(sanitize_address(addr, message.encoding)))

        # 6. Send via SendGrid API
        logger.info("[EMAIL DEBUG] attempting SendGrid send")
        response = self._sg.client.mail.send.post(request_body=mail_obj.get())
        logger.info("[EMAIL DEBUG] SendGrid response status: %s", response.status_code)
        if response.status_code >= 400:
            raise RuntimeError(f'SendGrid API error {response.status_code}: {response.body}')