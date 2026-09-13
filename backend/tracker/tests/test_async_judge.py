from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tracker.models import Problem, TestCase as ProblemTestCase, Submission
from tracker.tasks import run_submission_task
from tracker.services.judge_service import create_pending_submission

User = get_user_model()

class AsyncJudgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='async_judge_user', password='password123')
        self.other_user = User.objects.create_user(username='other_judge_user', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.problem = Problem.objects.create(
            question_number=201,
            title='Multiply Two Numbers',
            slug='multiply-two-numbers',
            difficulty='Easy',
            execution_mode='STDIN_STDOUT',
            description="Multiply two numbers.",
        )

        self.tc1 = ProblemTestCase.objects.create(
            problem=self.problem,
            input_text='3 4',
            expected_output='12',
            is_hidden=False,
            order=1,
        )

    @patch('tracker.tasks.run_submission_task.delay')
    def test_submit_endpoint_returns_202_accepted(self, mock_delay):
        payload = {
            'problem_id': str(self.problem.id),
            'language': 'python',
            'source_code': 'import sys\na, b = map(int, sys.stdin.read().split())\nprint(a * b)'
        }
        response = self.client.post('/api/submit/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('submission_id', response.data)
        self.assertEqual(response.data['verdict'], 'PENDING')
        mock_delay.assert_called_once()

    @patch('tracker.tasks.run_submission_task.delay')
    def test_duplicate_pending_submission_returns_409_conflict(self, mock_delay):
        # Create a pending submission
        pending_sub = create_pending_submission(
            self.user,
            str(self.problem.id),
            'python',
            'print(1)'
        )
        self.assertEqual(pending_sub.verdict, 'PENDING')

        payload = {
            'problem_id': str(self.problem.id),
            'language': 'python',
            'source_code': 'print(2)'
        }
        response = self.client.post('/api/submit/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.data)

    def test_submission_status_endpoint(self):
        sub = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            language='python',
            source_code='print(12)',
            verdict='PENDING',
            tests_passed=0,
            tests_total=1,
        )

        response = self.client.get(f'/api/submissions/{sub.id}/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['submission_id'], str(sub.id))
        self.assertEqual(response.data['verdict'], 'PENDING')
        self.assertEqual(response.data['tests_passed'], 0)
        self.assertEqual(response.data['tests_total'], 1)

    def test_submission_status_ownership_isolation(self):
        # Submission belongs to other_user
        sub = Submission.objects.create(
            user=self.other_user,
            problem=self.problem,
            language='python',
            source_code='print(12)',
            verdict='PENDING',
        )

        # Authenticated as self.user
        response = self.client.get(f'/api/submissions/{sub.id}/status/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_celery_task_executes_submission_to_accepted(self):
        code = 'import sys\na, b = map(int, sys.stdin.read().split())\nprint(a * b)'
        sub = create_pending_submission(self.user, str(self.problem.id), 'python', code)
        self.assertEqual(sub.verdict, 'PENDING')

        # Run Celery task directly
        result = run_submission_task(str(sub.id))
        self.assertEqual(result['verdict'], 'ACCEPTED')

        sub.refresh_from_db()
        self.assertEqual(sub.verdict, 'ACCEPTED')
        self.assertEqual(sub.tests_passed, 1)
        self.assertEqual(sub.tests_total, 1)
