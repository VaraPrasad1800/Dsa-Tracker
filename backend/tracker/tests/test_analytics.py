from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from tracker.models import Problem, Tag, UserProblemProgress
from tracker.services.leitner import update_problem_progress
from tracker.services.analytics import (
    get_user_streaks, get_user_topic_breakdown, get_user_difficulty_breakdown,
    get_user_heatmap, invalidate_user_analytics_cache
)

User = get_user_model()

class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analytics_user', password='password')
        self.tag_array = Tag.objects.create(name='Array', slug='array')
        self.tag_graph = Tag.objects.create(name='Graph', slug='graph')

        self.p_easy = Problem.objects.create(title='Easy 1', slug='easy-1', difficulty='Easy')
        self.p_easy.tags.add(self.tag_array)

        self.p_hard = Problem.objects.create(title='Hard 1', slug='hard-1', difficulty='Hard')
        self.p_hard.tags.add(self.tag_graph)

    def test_streaks_and_breakdowns(self):
        # Solve easy problem
        update_problem_progress(self.user, self.p_easy, status='SOLVED')

        streaks = get_user_streaks(self.user)
        self.assertEqual(streaks['current_streak'], 1)

        diff = get_user_difficulty_breakdown(self.user)
        self.assertEqual(diff['Easy']['solved'], 1)
        self.assertEqual(diff['Hard']['solved'], 0)

        topics = get_user_topic_breakdown(self.user)
        array_topic = next(t for t in topics['topics'] if t['name'] == 'Array')
        graph_topic = next(t for t in topics['topics'] if t['name'] == 'Graph')
        self.assertEqual(array_topic['percentage'], 100.0)
        self.assertEqual(graph_topic['percentage'], 0.0)
        self.assertTrue(graph_topic['is_weak'])
