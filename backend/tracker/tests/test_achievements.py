from django.test import TestCase
from django.contrib.auth import get_user_model
from tracker.models import Problem, UserProblemProgress, Achievement, UserAchievement
from tracker.services.achievement_service import seed_achievements, check_and_unlock_achievements, get_user_achievements

User = get_user_model()

class AchievementSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='achieve_user', password='password123')
        seed_achievements()

    def test_first_solve_unlock(self):
        problem = Problem.objects.create(title='Two Sum', slug='two-sum', difficulty='Easy')
        UserProblemProgress.objects.create(user=self.user, problem=problem, status='SOLVED')

        unlocked = check_and_unlock_achievements(self.user)
        self.assertTrue(any(a.code == 'FIRST_SOLVE' for a in unlocked))
        self.assertEqual(UserAchievement.objects.filter(user=self.user, achievement__code='FIRST_SOLVE').count(), 1)

    def test_idempotent_unlock(self):
        problem = Problem.objects.create(title='Two Sum', slug='two-sum', difficulty='Easy')
        UserProblemProgress.objects.create(user=self.user, problem=problem, status='SOLVED')

        unlocked1 = check_and_unlock_achievements(self.user)
        unlocked2 = check_and_unlock_achievements(self.user)
        self.assertEqual(len(unlocked2), 0)

    def test_get_user_achievements_status(self):
        data = get_user_achievements(self.user)
        self.assertTrue(len(data) > 0)
        self.assertIn('code', data[0])
        self.assertIn('unlocked', data[0])
