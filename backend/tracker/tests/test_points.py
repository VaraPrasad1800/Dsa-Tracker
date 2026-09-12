from django.test import TestCase
from django.contrib.auth import get_user_model
from tracker.models import UserPoints, ActivityEvent
from tracker.services.points_service import (
    award_points, award_challenge_points, award_streak_points, get_user_points, reset_weekly_points
)

User = get_user_model()

class PointsSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='points_user', password='password123')

    def test_award_points(self):
        award_points(self.user, reason='first_solve_easy', amount=10)
        pts = get_user_points(self.user)
        self.assertEqual(pts['total'], 10)
        self.assertEqual(pts['weekly'], 10)
        self.assertEqual(ActivityEvent.objects.filter(user=self.user, event_type='POINTS_AWARDED').count(), 1)

    def test_award_challenge_points(self):
        award_challenge_points(self.user, amount=50, bonus=25)
        pts = get_user_points(self.user)
        self.assertEqual(pts['total'], 75)
        self.assertEqual(pts['challenge_points'], 75)

    def test_award_streak_points(self):
        award_streak_points(self.user, streak_days=7, amount=25)
        pts = get_user_points(self.user)
        self.assertEqual(pts['total'], 25)
        self.assertEqual(pts['streak_points'], 25)

    def test_weekly_reset(self):
        award_points(self.user, reason='solve', amount=50)
        reset_weekly_points(self.user)
        pts = get_user_points(self.user)
        self.assertEqual(pts['weekly'], 0)
        self.assertEqual(pts['total'], 50)
