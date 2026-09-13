from unittest.mock import patch
from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tracker.models import Problem, TestCase as ProblemTestCase, Submission

User = get_user_model()


class JudgeThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='throttle_user', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.problem = Problem.objects.create(
            question_number=301,
            title='Throttle Test Problem',
            slug='throttle-test-problem',
            difficulty='Easy',
            execution_mode='STDIN_STDOUT',
            description="Simple test problem.",
        )
        self.tc = ProblemTestCase.objects.create(
            problem=self.problem,
            input_text='hello',
            expected_output='hello',
            is_hidden=False,
            order=1,
        )

    def tearDown(self):
        cache.clear()

    @patch('tracker.services.judge_service.run_code_for_user')
    def test_run_code_throttle_limit_10_per_minute(self, mock_run):
        mock_run.return_value = {
            'status': 'OK',
            'stdout': 'hello',
            'stderr': '',
            'execution_time_ms': 10,
            'memory_kb': 1024,
            'time_limit_ms': 1000,
        }

        payload = {
            'problem_id': str(self.problem.id),
            'language': 'python',
            'source_code': 'print("hello")',
            'stdin': '',
        }

        # 10 requests should succeed (HTTP 200)
        for i in range(10):
            response = self.client.post('/api/run-code/', payload, format='json')
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Request {i+1} failed with status {response.status_code}: {response.data}"
            )

        # 11th request within the same minute should be throttled (HTTP 429)
        response_11 = self.client.post('/api/run-code/', payload, format='json')
        self.assertEqual(response_11.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Retry-After', response_11.headers)

    @patch('tracker.tasks.run_submission_task.delay')
    def test_submit_code_throttle_limit_5_per_minute(self, mock_delay):
        payload = {
            'problem_id': str(self.problem.id),
            'language': 'python',
            'source_code': 'print("hello")',
        }

        # First 5 submits should be accepted (HTTP 202).
        # We delete/update previous submission each time so the pending check doesn't 409.
        for i in range(5):
            # Clean up pending submissions to isolate the rate throttle from the 409 pending check
            Submission.objects.filter(user=self.user, problem=self.problem, verdict='PENDING').update(verdict='ACCEPTED')
            response = self.client.post('/api/submit/', payload, format='json')
            self.assertEqual(
                response.status_code,
                status.HTTP_202_ACCEPTED,
                f"Request {i+1} failed with status {response.status_code}: {response.data}"
            )

        # Clean up pending submissions again before 6th request
        Submission.objects.filter(user=self.user, problem=self.problem, verdict='PENDING').update(verdict='ACCEPTED')

        # 6th submit within the same minute should be throttled (HTTP 429)
        response_6 = self.client.post('/api/submit/', payload, format='json')
        self.assertEqual(response_6.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Retry-After', response_6.headers)

    def test_duplicate_pending_submission_returns_409(self):
        Submission.objects.create(
            user=self.user,
            problem=self.problem,
            language='python',
            source_code='print(1)',
            verdict='PENDING',
        )

        payload = {
            'problem_id': str(self.problem.id),
            'language': 'python',
            'source_code': 'print(2)',
        }
        response = self.client.post('/api/submit/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data.get('error'),
            'You already have a pending submission for this problem. Please wait for it to complete.'
        )
