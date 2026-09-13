from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from tracker.models import Problem, Tag, UserProfile, UserProblemProgress
from tracker.authentication import generate_jwt_token

User = get_user_model()


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class FocusTopicsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(username='alice', password='password123')
        self.user_b = User.objects.create_user(username='bob', password='password123')
        self.auth_a = {'HTTP_AUTHORIZATION': f'Bearer {generate_jwt_token(self.user_a)}'}
        self.auth_b = {'HTTP_AUTHORIZATION': f'Bearer {generate_jwt_token(self.user_b)}'}

        # Ensure profiles exist
        self.profile_a, _ = UserProfile.objects.get_or_create(user=self.user_a)
        self.profile_b, _ = UserProfile.objects.get_or_create(user=self.user_b)

        # Create sample tags
        self.tag_arrays = Tag.objects.create(name='Arrays', slug='arrays', color='#3b82f6')
        self.tag_dp = Tag.objects.create(name='Dynamic Programming', slug='dynamic-programming', color='#8b5cf6')
        self.tag_graphs = Tag.objects.create(name='Graphs', slug='graphs', color='#10b981')
        self.tag_trees = Tag.objects.create(name='Trees', slug='trees', color='#f59e0b')
        self.tag_strings = Tag.objects.create(name='Strings', slug='strings', color='#ec4899')
        self.tag_math = Tag.objects.create(name='Math', slug='math', color='#06b6d4')

        # Create sample problems
        self.prob1 = Problem.objects.create(title='Two Sum', slug='two-sum', difficulty='Easy')
        self.prob1.tags.add(self.tag_arrays)

        self.prob2 = Problem.objects.create(title='Coin Change', slug='coin-change', difficulty='Medium')
        self.prob2.tags.add(self.tag_dp)

        self.prob3 = Problem.objects.create(title='Network Delay', slug='network-delay', difficulty='Medium')
        self.prob3.tags.add(self.tag_graphs)

        self.prob4 = Problem.objects.create(title='Invert Tree', slug='invert-tree', difficulty='Easy')
        self.prob4.tags.add(self.tag_trees)

    def test_default_focus_topics_fallback_to_auto(self):
        """When user has not selected focus topics, GET returns auto-detected weak topics."""
        url = reverse('user-focus-topics')
        res = self.client.get(url, **self.auth_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['is_custom'])
        self.assertTrue(len(res.data['focus_topics']) > 0)

    def test_set_custom_focus_topics(self):
        """User can set up to 5 custom focus topics by id or slug."""
        url = reverse('user-focus-topics')
        payload = {
            'topic_ids': ['dynamic-programming', 'graphs']
        }
        res = self.client.put(url, data=payload, format='json', **self.auth_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['is_custom'])
        topic_names = [t['name'] for t in res.data['focus_topics']]
        self.assertIn('Dynamic Programming', topic_names)
        self.assertIn('Graphs', topic_names)
        self.assertEqual(len(topic_names), 2)

    def test_custom_focus_topics_max_limit(self):
        """Setting more than 5 focus topics returns a 400 validation error."""
        url = reverse('user-focus-topics')
        payload = {
            'topic_ids': ['arrays', 'dynamic-programming', 'graphs', 'trees', 'strings', 'math']
        }
        res = self.client.put(url, data=payload, format='json', **self.auth_a)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Maximum 5', res.data['error'])

    def test_reset_focus_topics_to_auto(self):
        """Passing an empty list clears custom focus topics and reverts to auto."""
        url = reverse('user-focus-topics')
        self.client.put(url, data={'topic_ids': ['graphs']}, format='json', **self.auth_a)

        res = self.client.put(url, data={'topic_ids': []}, format='json', **self.auth_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['is_custom'])

    def test_user_isolation(self):
        """User A's custom focus topics do not affect User B."""
        url = reverse('user-focus-topics')
        self.client.put(url, data={'topic_ids': ['graphs']}, format='json', **self.auth_a)

        res_b = self.client.get(url, **self.auth_b)
        self.assertFalse(res_b.data['is_custom'])

    def test_stats_view_reflects_custom_focus(self):
        """UserProgressStatsView includes custom focus topics and flag."""
        self.profile_a.focus_topics.set([self.tag_graphs, self.tag_dp])

        stats_url = reverse('user-progress-stats')
        res = self.client.get(stats_url, **self.auth_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['is_custom_focus'])
        self.assertEqual(len(res.data['weak_topics']), 2)
        self.assertIn('Graphs', res.data['weak_topics'])
        self.assertIn('Dynamic Programming', res.data['weak_topics'])

    def test_topic_practice_endpoint(self):
        """Topic practice returns prioritized problems and target problem."""
        UserProblemProgress.objects.create(
            user=self.user_a,
            problem=self.prob2,
            status='NEEDS_REVISIT'
        )

        url = reverse('topic-practice') + '?topic=dynamic-programming'
        res = self.client.get(url, **self.auth_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['topic']['name'], 'Dynamic Programming')
        self.assertEqual(len(res.data['problems']), 1)
        self.assertEqual(res.data['target_problem']['id'], str(self.prob2.id))
