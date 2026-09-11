"""
Shared auth-token helpers for email verification and password reset.

Centralizes token generation, hashing, expiry checks, and the create helpers
used by both the auth views and the send_test_email management command.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def generate_auth_token():
    """Generate a URL-safe random token for email verification / password reset."""
    return secrets.token_urlsafe(40)


def hash_token(token):
    """Hash a token for secure storage (single-use, stored hashed)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def is_token_expired(sent_at, expiry_hours):
    if not sent_at:
        return True
    return timezone.now() - sent_at > timedelta(hours=expiry_hours)


def create_verification_token(profile):
    """Generate, store (hashed), and return a fresh email-verification token."""
    token = generate_auth_token()
    profile.email_verification_token_hash = hash_token(token)
    profile.email_verification_sent_at = timezone.now()
    profile.save(update_fields=['email_verification_token_hash', 'email_verification_sent_at'])
    return token


def create_password_reset_token(profile):
    """Generate, store (hashed), and return a fresh password-reset token."""
    token = generate_auth_token()
    profile.password_reset_token_hash = hash_token(token)
    profile.password_reset_sent_at = timezone.now()
    profile.save(update_fields=['password_reset_token_hash', 'password_reset_sent_at'])
    return token


def get_verification_expiry_hours():
    return getattr(settings, 'EMAIL_VERIFICATION_EXPIRY_HOURS', 24)


def get_password_reset_expiry_hours():
    return getattr(settings, 'PASSWORD_RESET_EXPIRY_HOURS', 1)