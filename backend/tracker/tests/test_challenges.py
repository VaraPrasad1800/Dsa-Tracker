from django.test import TestCase
from django.contrib.auth import get_user_model
from tracker.models import Problem, Submission, Challenge
from tracker.services.challenge_service import create_challenge, check_challenge_progress, finalize_challenge

User = get_user_model()

class ChallengeSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='chal_user', password='password123')
        self.problem = Problem.objects.create(title='Valid Parentheses', slug='valid-parentheses', difficulty='Easy')

    def test_create_and_progress_challenge(self):
        challenge = create_challenge(self.user, {
            'title': 'Solve 1 Easy Problem',
            'duration_minutes': 60,
            'target_count': 1,
            'difficulty_filter': 'Easy'
        })
        self.assertEqual(challenge.status, 'ACTIVE')

        # No submissions yet
        prog = check_challenge_progress(self.user, str(challenge.id))
        self.assertFalse(prog['is_complete'])
        self.assertEqual(prog['completed_count'], 0)

        # Submit accepted
        Submission.objects.create(
            user=self.user,
            problem=self.problem,
            language='python',
            source_code='pass',
            verdict='ACCEPTED'
        )

        prog2 = check_challenge_progress(self.user, str(challenge.id))
        self.assertTrue(prog2['is_complete'])
        self.assertEqual(prog2['completed_count'], 1)

        fin = finalize_challenge(challenge, self.user)
        self.assertEqual(fin['status'], 'COMPLETED')
        self.assertGreater(fin['points_earned'], 0)
