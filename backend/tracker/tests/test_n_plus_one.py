from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from tracker.models import Company, Tag, Problem, UserProblemProgress
from django.core.cache import cache

User = get_user_model()

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'test-n-plus-one'}})
class NPlusOneQueryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='querytester',
            email='querytester@example.com',
            password='Password123!'
        )
        self.client.force_authenticate(user=self.user)

    def test_company_list_no_n_plus_one(self):
        """
        Ensure GET /api/problems/companies/ runs in constant (<= 4) queries
        regardless of how many companies exist, with accurate solved counts.
        """
        companies = [
            Company(name=f'Company {i:03d}', slug=f'company-{i:03d}')
            for i in range(35)
        ]
        Company.objects.bulk_create(companies)
        all_companies = list(Company.objects.all())

        problems = [
            Problem(title=f'Problem {i}', slug=f'problem-{i}', difficulty='Easy', question_number=1000 + i)
            for i in range(10)
        ]
        Problem.objects.bulk_create(problems)
        all_problems = list(Problem.objects.all())

        all_problems[0].companies.add(all_companies[0])
        all_problems[1].companies.add(all_companies[0])
        all_problems[2].companies.add(all_companies[1])

        UserProblemProgress.objects.create(user=self.user, problem=all_problems[0], status='SOLVED')
        UserProblemProgress.objects.create(user=self.user, problem=all_problems[2], status='SOLVED')

        with self.assertNumQueries(3):
            response = self.client.get('/api/problems/companies/')
        self.assertEqual(response.status_code, 200)

        data = response.data
        results = data.get('results', data)
        self.assertEqual(data.get('count', len(results)), 35)

        comp_0_data = next(c for c in results if c['slug'] == all_companies[0].slug)
        comp_1_data = next(c for c in results if c['slug'] == all_companies[1].slug)
        comp_2_data = next(c for c in results if c['slug'] == all_companies[2].slug)

        self.assertEqual(comp_0_data['user_progress']['solved'], 1)
        self.assertEqual(comp_1_data['user_progress']['solved'], 1)
        self.assertEqual(comp_2_data['user_progress']['solved'], 0)

        # Second request: served from cache in 0 database queries
        with self.assertNumQueries(0):
            cached_response = self.client.get('/api/problems/companies/')
        self.assertEqual(cached_response.status_code, 200)

    def test_tag_list_no_n_plus_one(self):
        """
        Ensure GET /api/problems/tags/ runs in constant (<= 3) queries
        regardless of how many tags exist, with accurate solved counts.
        """
        tags = [
            Tag(name=f'Tag {i:03d}', slug=f'tag-{i:03d}')
            for i in range(35)
        ]
        Tag.objects.bulk_create(tags)
        all_tags = list(Tag.objects.all())

        problems = [
            Problem(title=f'Tag Prob {i}', slug=f'tag-prob-{i}', difficulty='Medium', question_number=2000 + i)
            for i in range(5)
        ]
        Problem.objects.bulk_create(problems)
        all_problems = list(Problem.objects.all())

        all_problems[0].tags.add(all_tags[0])
        all_problems[1].tags.add(all_tags[1])

        UserProblemProgress.objects.create(user=self.user, problem=all_problems[0], status='SOLVED')

        with self.assertNumQueries(2):
            response = self.client.get('/api/problems/tags/')
        self.assertEqual(response.status_code, 200)

        tag_0 = next(t for t in response.data if t['slug'] == all_tags[0].slug)
        tag_1 = next(t for t in response.data if t['slug'] == all_tags[1].slug)
        self.assertEqual(tag_0['user_progress']['solved'], 1)
        self.assertEqual(tag_1['user_progress']['solved'], 0)

    def test_due_today_no_n_plus_one(self):
        """
        Ensure GET /api/user-progress/due-today/ runs in constant queries (<= 4).
        """
        company = Company.objects.create(name='Review Co', slug='review-co')
        tag = Tag.objects.create(name='Review Tag', slug='review-tag')

        problems = [
            Problem(title=f'Due Prob {i}', slug=f'due-prob-{i}', difficulty='Hard', question_number=3000 + i)
            for i in range(20)
        ]
        Problem.objects.bulk_create(problems)
        all_problems = list(Problem.objects.all())

        now = timezone.now()
        past = now - timedelta(days=1)
        for p in all_problems:
            p.companies.add(company)
            p.tags.add(tag)
            UserProblemProgress.objects.create(
                user=self.user,
                problem=p,
                status='NEEDS_REVISIT',
                current_box=1,
                next_review_date=past
            )

        with self.assertNumQueries(4):
            response = self.client.get('/api/user-progress/due-today/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 20)

    def test_analytics_topic_breakdown_and_mastery_no_n_plus_one(self):
        """
        Ensure get_user_topic_breakdown and get_topic_mastery run in constant queries
        (2 and 3 queries respectively) even with 35 tags.
        """
        from tracker.services.analytics import get_user_topic_breakdown, get_topic_mastery_levels
        tags = [
            Tag(name=f'Analytics Tag {i:03d}', slug=f'analytics-tag-{i:03d}')
            for i in range(35)
        ]
        Tag.objects.bulk_create(tags)
        all_tags = list(Tag.objects.all())

        p = Problem.objects.create(title='P1', slug='p1', difficulty='Medium', question_number=4000)
        p.tags.add(*all_tags)
        UserProblemProgress.objects.create(user=self.user, problem=p, status='SOLVED')

        with self.assertNumQueries(2):
            breakdown = get_user_topic_breakdown(self.user)
        self.assertEqual(len(breakdown['topics']), 35)

        cache.clear()
        with self.assertNumQueries(3):
            mastery = get_topic_mastery_levels(self.user)
        self.assertEqual(len(mastery['topics']), 35)
