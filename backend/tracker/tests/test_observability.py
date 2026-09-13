import logging
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from tracker.middleware import RequestIDMiddleware, RequestIDFilter, get_current_request_id


class ObservabilityTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_request_generates_x_request_id_header(self):
        """Any standard API request must return an X-Request-ID header."""
        response = self.client.get('/api/problems/')
        self.assertIn('X-Request-ID', response.headers)
        request_id = response.headers['X-Request-ID']
        self.assertTrue(len(request_id) >= 16)

    def test_request_preserves_incoming_x_request_id(self):
        """If an upstream proxy provides X-Request-ID, the middleware preserves it."""
        custom_id = 'trace-id-abc-123-xyz-789'
        response = self.client.get('/api/problems/', HTTP_X_REQUEST_ID=custom_id)
        self.assertEqual(response.headers.get('X-Request-ID'), custom_id)

    def test_consecutive_requests_have_unique_request_ids(self):
        """Different requests must generate distinct request IDs."""
        res1 = self.client.get('/api/problems/')
        res2 = self.client.get('/api/problems/')
        self.assertNotEqual(res1.headers['X-Request-ID'], res2.headers['X-Request-ID'])

    def test_logging_filter_captures_current_request_id(self):
        """RequestIDFilter injects the active request_id context into log records."""
        custom_id = 'test-log-id-555'

        def dummy_view(request):
            log_filter = RequestIDFilter()
            record = logging.LogRecord(
                name='test_logger',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg='Test log',
                args=(),
                exc_info=None,
            )
            log_filter.filter(record)
            self.assertEqual(record.request_id, custom_id)
            self.assertEqual(get_current_request_id(), custom_id)
            return HttpResponse('ok')

        middleware = RequestIDMiddleware(dummy_view)
        req = self.factory.get('/', HTTP_X_REQUEST_ID=custom_id)
        middleware(req)
