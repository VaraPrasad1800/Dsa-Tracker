import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries
from rest_framework.test import APIClient
from tracker.models import Problem, Tag, Company, UserProblemProgress, UserProfile

User = get_user_model()


class ProblemListPerformanceAndUniquenessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='perftest',
            email='perftest@example.com',
            password='testpassword123'
        )
        cls.profile = UserProfile.objects.create(user=cls.user)

        # Create multiple tags and companies to test M2M duplication
        cls.tag1 = Tag.objects.create(name='Array', slug='array', color='#3b82f6')
        cls.tag2 = Tag.objects.create(name='String', slug='string', color='#10b981')
        cls.tag3 = Tag.objects.create(name='Dynamic Programming', slug='dynamic-programming', color='#8b5cf6')

        cls.comp1 = Company.objects.create(name='Google', slug='google')
        cls.comp2 = Company.objects.create(name='Meta', slug='meta')
        cls.comp3 = Company.objects.create(name='Amazon', slug='amazon')
        cls.comp4 = Company.objects.create(name='Apple', slug='apple')

        # Create 25 problems with overlapping tags and companies
        cls.problems = []
        for i in range(1, 26):
            diff = 'Easy' if i % 3 == 0 else ('Medium' if i % 3 == 1 else 'Hard')
            p = Problem.objects.create(
                question_number=i,
                title=f'Problem #{i} Sample Title',
                slug=f'problem-{i}-sample-title',
                difficulty=diff,
                description=f'This is problem description for problem #{i} with lots of text...' * 5,
                frequency=i * 2,
            )
            # Add multiple tags & companies
            p.tags.add(cls.tag1, cls.tag2, cls.tag3)
            p.companies.add(cls.comp1, cls.comp2, cls.comp3, cls.comp4)
            cls.problems.append(p)

        # Create progress and bookmarks for user on some problems
        for p in cls.problems[:10]:
            UserProblemProgress.objects.create(
                user=cls.user,
                problem=p,
                status='SOLVED' if p.question_number % 2 == 0 else 'NEEDS_REVISIT',
                times_solved=1,
                current_box=2,
            )
            cls.profile.bookmarked_problems.add(p)

    def setUp(self):
        self.client = APIClient()

    def test_authenticated_problem_list_query_count_is_bounded(self):
        """
        Verify that GET /api/problems/ executes in <= 12 SQL queries,
        completely avoiding the previous N+1 query explosion.
        """
        self.client.force_authenticate(user=self.user)
        reset_queries()

        response = self.client.get('/api/problems/?page=1&page_size=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 20)

        query_count = len(connection.queries)
        # Bounded constant queries (aggregate counts, paginator count, slice, prefetch tags/comps, batch progress, bookmarks)
        self.assertLessEqual(query_count, 12, f'Expected <= 12 queries, got {query_count}')

    def test_search_and_filters_produce_zero_duplicates(self):
        """
        Verify that filtering across ManyToMany relations (tags, companies, search)
        never produces duplicate problem entries on a page.
        """
        self.client.force_authenticate(user=self.user)

        test_urls = [
            '/api/problems/?search=Sample',
            '/api/problems/?search=Problem',
            '/api/problems/?topic=Array',
            '/api/problems/?topic=String',
            '/api/problems/?company=Google',
            '/api/problems/?company=Meta',
            '/api/problems/?difficulty=Medium',
            '/api/problems/?sort=random',
            '/api/problems/?sort=frequency',
            '/api/problems/?sort=question_number',
        ]

        for url in test_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200)
                results = res.data.get('results', [])
                ids = [p['id'] for p in results]
                self.assertEqual(len(ids), len(set(ids)), f'Duplicates found in {url}')

    def test_pagination_stability_has_zero_overlap(self):
        """
        Verify that page 1 and page 2 have zero overlapping problems when paginating.
        """
        sort_options = ['question_number', 'difficulty_asc', 'difficulty_desc', 'frequency', 'title']

        for sort in sort_options:
            with self.subTest(sort=sort):
                p1_res = self.client.get(f'/api/problems/?sort={sort}&page=1&page_size=10')
                p2_res = self.client.get(f'/api/problems/?sort={sort}&page=2&page_size=10')

                self.assertEqual(p1_res.status_code, 200)
                self.assertEqual(p2_res.status_code, 200)

                p1_ids = set(p['id'] for p in p1_res.data['results'])
                p2_ids = set(p['id'] for p in p2_res.data['results'])

                overlap = p1_ids.intersection(p2_ids)
                self.assertEqual(len(overlap), 0, f'Overlap found between p1 and p2 for sort={sort}: {overlap}')

    def test_problem_list_serializer_does_not_leak_full_description(self):
        """
        Verify that ProblemListSerializer returns lightweight cards without massive description fields.
        """
        res = self.client.get('/api/problems/?page=1&page_size=5')
        self.assertEqual(res.status_code, 200)
        results = res.data['results']
        self.assertGreater(len(results), 0)

        # description should not be present on list objects
        for p in results:
            self.assertNotIn('description', p)
            self.assertIn('question_number', p)
            self.assertIn('title', p)
            self.assertIn('difficulty', p)
            self.assertIn('tags', p)
            self.assertIn('companies', p)

    def test_filter_counts_aggregation_accuracy(self):
        """
        Verify that aggregate difficulty and progress counts are accurate.
        """
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/problems/')
        self.assertEqual(res.status_code, 200)

        counts = res.data['counts']
        self.assertEqual(counts['total'], 25)
        self.assertEqual(counts['easy'] + counts['medium'] + counts['hard'], 25)
        self.assertGreater(counts['solved'], 0)
        self.assertGreater(counts['needs_revisit'], 0)
        self.assertEqual(counts['bookmarked'], 10)
