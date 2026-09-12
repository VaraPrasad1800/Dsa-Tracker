from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tracker.models import Problem, InterviewSession

User = get_user_model()

class InterviewSimulationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='interviewee', password='password123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.p1 = Problem.objects.create(title='P1', slug='p1', difficulty='Medium')
        self.p2 = Problem.objects.create(title='P2', slug='p2', difficulty='Medium')

    def test_start_and_end_interview_session(self):
        # Start session
        res = self.client.post('/api/interview-sessions/', {
            'duration_minutes': 45,
            'num_problems': 2,
            'difficulty': 'Medium'
        })
        self.assertEqual(res.status_code, 201)
        session_id = res.data['id']
        self.assertEqual(len(res.data['interview_problems']), 2)

        # Mark problem 1 solved
        solve_res = self.client.post(f'/api/interview-sessions/{session_id}/problems/{self.p1.id}/solve/')
        self.assertEqual(solve_res.status_code, 200)

        # End session
        end_res = self.client.post(f'/api/interview-sessions/{session_id}/end/')
        self.assertEqual(end_res.status_code, 200)
        self.assertEqual(end_res.data['status'], 'COMPLETED')
        self.assertEqual(end_res.data['problems_solved'], 1)
        self.assertGreater(end_res.data['score'], 0)
        self.assertIn('follow_up_actions', end_res.data)
