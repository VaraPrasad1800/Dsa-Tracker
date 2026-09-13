"""
JWT Authentication for DSA Tracker.

Provides a custom authentication class that uses JWT tokens from Authorization header,
while maintaining backward compatibility with X-Demo-User header for demo mode.
"""
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions

User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT authentication class.

    Supports both:
    1. Authorization: Bearer <jwt_token> - standard JWT auth
    2. Authorization: Token <drf_token> - legacy DRF token auth (fallback)
    3. X-Demo-User header - demo mode (handled in views for backward compat)

    The JWT payload should contain: {'user_id': <id>, 'username': <username>, 'exp': <timestamp>}
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).split()

        if not auth_header:
            return None

        if len(auth_header) != 2:
            raise exceptions.AuthenticationFailed('Invalid authorization header format.')

        auth_type = auth_header[0].decode('utf-8').lower()
        token = auth_header[1].decode('utf-8')

        # Handle standard JWT Bearer tokens
        if auth_type == 'bearer':
            return self._authenticate_jwt(token)

        # Handle legacy DRF TokenAuthentication (Token <key>)
        if auth_type == 'token':
            return self._authenticate_drf_token(token)

        return None

    def _authenticate_jwt(self, token):
        """Validate JWT token and return user."""
        try:
            # Get JWT secret from settings
            secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
            algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')

            payload = jwt.decode(token, secret, algorithms=[algorithm])

            user_id = payload.get('user_id')
            username = payload.get('username')

            if not user_id:
                raise exceptions.AuthenticationFailed('Invalid token: missing user_id.')

            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found.')

            if not user.is_active:
                raise exceptions.AuthenticationFailed('User inactive or deleted.')

            return (user, None)

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')

    def _authenticate_drf_token(self, token):
        """Fallback to DRF's built-in token authentication."""
        from rest_framework.authtoken.models import Token

        try:
            token_obj = Token.objects.select_related('user').get(key=token)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token_obj.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        return (token_obj.user, None)

    def authenticate_header(self, request):
        return 'Bearer'


def generate_jwt_token(user, token_type='access'):
    """
    Generate a JWT token for a user.

    Returns a JWT string with payload containing user_id, username, token_type, and expiration.
    """
    from datetime import datetime, timedelta

    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    expiration_hours = getattr(settings, 'JWT_EXPIRATION_HOURS', 1) if token_type == 'access' \
        else getattr(settings, 'JWT_REFRESH_EXPIRATION_HOURS', 24 * 7)

    import uuid

    now = datetime.utcnow()
    payload = {
        'user_id': user.pk,
        'username': user.username,
        'token_type': token_type,
        'exp': now + timedelta(hours=expiration_hours),
        'iat': now,
        'jti': uuid.uuid4().hex,
    }

    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token


def generate_jwt_tokens(user):
    """
    Generate a pair of JWT access + refresh tokens for a user,
    and persist the refresh token hash in the RefreshToken model.
    """
    from tracker.models import RefreshToken
    from tracker.services.auth_tokens import hash_token
    from django.utils import timezone
    from datetime import timedelta

    access = generate_jwt_token(user, token_type='access')
    refresh = generate_jwt_token(user, token_type='refresh')

    refresh_hours = getattr(settings, 'JWT_REFRESH_EXPIRATION_HOURS', 24 * 7)
    expires_at = timezone.now() + timedelta(hours=refresh_hours)

    RefreshToken.objects.create(
        user=user,
        token_hash=hash_token(refresh),
        expires_at=expires_at,
        revoked=False,
    )

    return {'access': access, 'refresh': refresh}


def decode_jwt_token(token):
    """Decode and validate a JWT token, returning the payload or raising."""
    import jwt as _jwt
    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    return _jwt.decode(token, secret, algorithms=[algorithm])


try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
        target_class = 'tracker.authentication.JWTAuthentication'
        name = 'jwtAuth'

        def get_security_requirement(self, auto_schema):
            return {self.name: []}

        def get_security_definition(self, auto_schema):
            return {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
except ImportError:
    pass