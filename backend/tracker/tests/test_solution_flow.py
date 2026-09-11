import uuid
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from tracker.models import Problem, Solution
from tracker.authentication import generate_jwt_token
from tracker.scraper import _scraper

User = get_user_model()

PAGE1_HTML = """
<!DOCTYPE html>
<html>
<body>
    <h1>158. Read N Characters Given Read4 II - Call multiple times</h1>
    <div class="markdown-body div-width">
        <p>Given a file and assume read4 exists, read n characters.</p>
        <pre>Example 1: read(buf, 1)</pre>
        <div>
            <h3>Problem Solution</h3>
            <a href="https://leetcode.ca/2016-05-06-158-Read-N-Characters-Given-Read4-II/">158-Read-N-Characters</a>
        </div>
    </div>
</body>
</html>
"""

PAGE2_HTML = """
<!DOCTYPE html>
<html>
<body>
    <h1 id="question">Question</h1>
    <p>Given a file and assume read4 exists, read n characters.</p>
    <h1 id="algorithm">Algorithm</h1>
    <p>Maintain readPos and writePos pointers.</p>
    <h1 id="code">Code</h1>
    <ul class="uk-tab">
        <li><a>Java</a></li>
        <li><a>Python</a></li>
    </ul>
    <ul class="uk-switcher">
        <li>
            <div class="language-java">
                <pre><code>public class Solution {}</code></pre>
            </div>
        </li>
        <li>
            <div class="language-python">
                <pre><code># // Time: O(N)
# // Space: O(1)
class Solution:
    def read(self, buf, n):
        pass
</code></pre>
            </div>
        </li>
    </ul>
</body>
</html>
"""

class SolutionFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='test_dev', password='password123')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {generate_jwt_token(self.user)}'}

        self.problem = Problem.objects.create(
            title='Read N Characters Given read4 II',
            slug='read-n-characters-given-read4-ii',
            difficulty='Hard',
            leetcode_id=158,
            source_platform='LeetCode'
        )

    def test_dynamic_url_generation_and_two_stage_scraping(self):
        with patch.object(_scraper, '_fetch_html') as mock_fetch:
            def side_effect(url):
                if 'all/158.html' in url:
                    return PAGE1_HTML
                if '2016-05-06-158-Read-N-Characters-Given-Read4-II' in url:
                    return PAGE2_HTML
                return None

            mock_fetch.side_effect = side_effect
            scraped = _scraper.scrape(158)

            self.assertIsNotNone(scraped)
            self.assertEqual(scraped['question_number'], 158)
            self.assertEqual(scraped['title'], 'Read N Characters Given Read4 II - Call multiple times')
            self.assertIn('Given a file', scraped['description'])
            self.assertIn('readPos and writePos', scraped['explanation'])
            self.assertEqual(scraped['language'], 'python')
            self.assertIn('class Solution:', scraped['code'])
            self.assertEqual(scraped['time_complexity'], 'O(N)')
            self.assertEqual(scraped['space_complexity'], 'O(1)')
            self.assertEqual(scraped['source_url'], 'https://leetcode.ca/all/158.html')
            self.assertEqual(scraped['solution_source_url'], 'https://leetcode.ca/2016-05-06-158-Read-N-Characters-Given-Read4-II/')

    def test_solution_endpoint_cache_hit_and_miss(self):
        url = reverse('problem-solution', kwargs={'pk': self.problem.id})

        # 1. Cache Miss -> Triggers scrape and caches result
        with patch.object(_scraper, '_fetch_html') as mock_fetch:
            mock_fetch.side_effect = lambda u: PAGE1_HTML if 'all/158.html' in u else PAGE2_HTML
            res1 = self.client.get(url, **self.auth)

            self.assertEqual(res1.status_code, status.HTTP_200_OK)
            self.assertTrue(res1.data['available'])
            self.assertEqual(res1.data['question_number'], 158)
            self.assertEqual(res1.data['language'], 'python')
            self.assertEqual(mock_fetch.call_count, 2)

            # Assert record in DB
            sol = Solution.objects.get(problem=self.problem)
            self.assertEqual(sol.question_number, 158)
            self.assertFalse(sol.fetch_failed)
            self.assertTrue(sol.is_fresh)

        # 2. Cache Hit -> 0 external HTTP requests
        with patch.object(_scraper, '_fetch_html') as mock_fetch:
            res2 = self.client.get(url, **self.auth)
            self.assertEqual(res2.status_code, status.HTTP_200_OK)
            self.assertEqual(res2.data['code'], res1.data['code'])
            self.assertEqual(mock_fetch.call_count, 0)

    def test_stale_cache_refetches(self):
        url = reverse('problem-solution', kwargs={'pk': self.problem.id})
        Solution.objects.create(
            problem=self.problem,
            question_number=158,
            title='Old Title',
            description='Old Description',
            code='Old Code',
            language='python',
            source_url='https://leetcode.ca/all/158.html',
            last_fetched_at=timezone.now() - timezone.timedelta(days=8)
        )
        # Verify it is stale
        sol = Solution.objects.get(problem=self.problem)
        # Update last_fetched_at directly in DB because auto_now overrides on save
        Solution.objects.filter(id=sol.id).update(last_fetched_at=timezone.now() - timezone.timedelta(days=8))
        sol.refresh_from_db()
        self.assertFalse(sol.is_fresh)

        with patch.object(_scraper, '_fetch_html') as mock_fetch:
            mock_fetch.side_effect = lambda u: PAGE1_HTML if 'all/158.html' in u else PAGE2_HTML
            res = self.client.get(url, **self.auth)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(mock_fetch.call_count, 2)
            sol.refresh_from_db()
            self.assertTrue(sol.is_fresh)

    def test_temporary_failure_and_retry_window(self):
        url = reverse('problem-solution', kwargs={'pk': self.problem.id})

        # Simulate 404 on external server
        with patch.object(_scraper, '_fetch_html', return_value=None):
            res_fail = self.client.get(url, **self.auth)
            self.assertEqual(res_fail.status_code, status.HTTP_404_NOT_FOUND)
            self.assertFalse(res_fail.data['available'])

            sol = Solution.objects.get(problem=self.problem)
            self.assertTrue(sol.fetch_failed)
            self.assertFalse(sol.should_retry_failed)

        # Within 1 hour, it rejects without hitting upstream
        with patch.object(_scraper, '_fetch_html') as mock_fetch:
            res_wait = self.client.get(url, **self.auth)
            self.assertEqual(res_wait.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(mock_fetch.call_count, 0)

        # After retry window (> 1 hour), it retries upstream
        Solution.objects.filter(problem=self.problem).update(last_fetched_at=timezone.now() - timezone.timedelta(minutes=70))
        with patch.object(_scraper, '_fetch_html') as mock_fetch:
            mock_fetch.side_effect = lambda u: PAGE1_HTML if 'all/158.html' in u else PAGE2_HTML
            res_retry = self.client.get(url, **self.auth)
            self.assertEqual(res_retry.status_code, status.HTTP_200_OK)
            self.assertEqual(mock_fetch.call_count, 2)
            sol.refresh_from_db()
            self.assertFalse(sol.fetch_failed)

    def test_missing_problem_or_no_leetcode_id(self):
        prob_no_id = Problem.objects.create(
            title='Custom Mock Problem',
            slug='custom-mock-problem',
            difficulty='Medium',
            leetcode_id=None
        )
        url = reverse('problem-solution', kwargs={'pk': prob_no_id.id})
        res = self.client.get(url, **self.auth)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(res.data['available'])
        self.assertIn('No LeetCode ID', res.data['message'])

        fake_uuid = uuid.uuid4()
        url_fake = reverse('problem-solution', kwargs={'pk': fake_uuid})
        res_fake = self.client.get(url_fake, **self.auth)
        self.assertEqual(res_fake.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res_fake.data['message'], 'Problem not found.')
