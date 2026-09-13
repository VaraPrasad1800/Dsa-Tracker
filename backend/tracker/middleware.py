import contextvars
import logging
import uuid

_request_id_ctx_var = contextvars.ContextVar('request_id', default='-')


def get_current_request_id():
    """Return the request ID for the current async task / thread context."""
    return _request_id_ctx_var.get('-')


class RequestIDFilter(logging.Filter):
    """Logging filter that injects the current request_id into log records."""

    def filter(self, record):
        record.request_id = get_current_request_id()
        return True


class RequestIDMiddleware:
    """
    Middleware that assigns a unique UUID4 request ID to every incoming request.
    - Exposes request.id and request.request_id
    - Sets contextvar for logging filter
    - Tags Sentry scope with request_id if Sentry is active
    - Returns X-Request-ID response header
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming_id = request.META.get('HTTP_X_REQUEST_ID')
        if incoming_id and len(incoming_id) <= 64:
            request_id = incoming_id
        else:
            request_id = uuid.uuid4().hex

        request.id = request_id
        request.request_id = request_id
        token = _request_id_ctx_var.set(request_id)

        try:
            import sentry_sdk
            if sentry_sdk.Hub.current.client:
                sentry_sdk.set_tag('request_id', request_id)
        except Exception:
            pass

        try:
            response = self.get_response(request)
        finally:
            _request_id_ctx_var.reset(token)

        response['X-Request-ID'] = request_id
        return response
