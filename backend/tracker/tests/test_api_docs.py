from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class ApiDocumentationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_schema_endpoint_returns_200(self):
        res = self.client.get('/api/schema/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should contain OpenAPI spec information
        self.assertIn('openapi', res.content.decode('utf-8').lower())

    def test_swagger_ui_endpoint_returns_200(self):
        res = self.client.get('/api/docs/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('swagger-ui', res.content.decode('utf-8').lower())

    def test_redoc_endpoint_returns_200(self):
        res = self.client.get('/api/redoc/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('redoc', res.content.decode('utf-8').lower())
