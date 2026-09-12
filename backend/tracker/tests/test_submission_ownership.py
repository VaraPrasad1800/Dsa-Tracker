from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tracker.models import Problem, Submission

User = get_user_model()

class SubmissionOwnershipTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')

        self.client1 = APIClient()
        self.client1.force_authenticate(user=self.user1)

        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

        self.problem = Problem.objects.create(title='P1', slug='p1', difficulty='Easy')

        self.sub1 = Submission.objects.create(
            user=self.user1,
            problem=self.problem,
            language='python',
            source_code='print("secret code 1")',
            verdict='ACCEPTED'
        )

    def test_user_cannot_access_other_user_submission_detail(self):
        res = self.client2.get(f'/api/submissions/{self.sub1.id}/')
        self.assertEqual(res.status_code, 404)

    def test_user_can_access_own_submission_detail(self):
        res = self.client1.get(f'/api/submissions/{self.sub1.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['source_code'], 'print("secret code 1")')
