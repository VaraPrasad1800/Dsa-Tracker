from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from tracker.models import Problem, Tag, Company, UserProblemProgress
from tracker.authentication import generate_jwt_token

User = get_user_model()

class ProblemTrackingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(username='user_a', password='password')
        self.user_b = User.objects.create_user(username='user_b', password='password')
        self.auth_a = {'HTTP_AUTHORIZATION': f'Bearer {generate_jwt_token(self.user_a)}'}
        self.auth_b = {'HTTP_AUTHORIZATION': f'Bearer {generate_jwt_token(self.user_b)}'}

        self.tag_array = Tag.objects.create(name='Array', slug='array')
        self.tag_dp = Tag.objects.create(name='Dynamic Programming', slug='dynamic-programming')
        self.comp_google = Company.objects.create(name='Google', slug='google')

        self.prob1 = Problem.objects.create(
            title='Two Sum', slug='two-sum', difficulty='Easy', source_platform='LeetCode'
        )
        self.prob1.tags.add(self.tag_array)
        self.prob1.companies.add(self.comp_google)

        self.prob2 = Problem.objects.create(
            title='Climbing Stairs', slug='climbing-stairs', difficulty='Easy', source_platform='LeetCode'
        )
        self.prob2.tags.add(self.tag_dp)

    def test_problem_list_and_filters(self):
        # Unfiltered
        response = self.client.get(reverse('problem-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

        # Filter by difficulty
        response = self.client.get(reverse('problem-list') + '?difficulty=Hard')
        self.assertEqual(len(response.data['results']), 0)

        # Filter by topic
        response = self.client.get(reverse('problem-list') + '?topic=Array')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Two Sum')

        # Filter by company
        response = self.client.get(reverse('problem-list') + '?company=Google')
        self.assertEqual(len(response.data['results']), 1)

    def test_user_progress_creation_and_isolation(self):
        # Unauthenticated posts are rejected (demo mode removed).
        anon = self.client.post(reverse('user-progress-create'), {
            'problem_id': str(self.prob1.id), 'status': 'SOLVED'
        }, format='json')
        self.assertEqual(anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # User A solves Problem 1
        res_a = self.client.post(reverse('user-progress-create'), {
            'problem_id': str(self.prob1.id),
            'status': 'SOLVED',
            'notes': 'Optimal solution with hash table'
        }, format='json', **self.auth_a)
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        self.assertEqual(res_a.data['status'], 'SOLVED')
        self.assertEqual(res_a.data['current_box'], 2)

        # Verify User B sees problem as UNSOLVED
        res_b = self.client.get(reverse('problem-detail', kwargs={'pk': self.prob1.id}), **self.auth_b)
        self.assertIsNone(res_b.data['user_progress'])

        # User A sees their progress
        res_a_detail = self.client.get(reverse('problem-detail', kwargs={'pk': self.prob1.id}), **self.auth_a)
        self.assertIsNotNone(res_a_detail.data['user_progress'])
        self.assertEqual(res_a_detail.data['user_progress']['status'], 'SOLVED')

    def test_company_list_and_search(self):
        Company.objects.create(name='Amazon', slug='amazon')
        Company.objects.create(name='Microsoft', slug='microsoft')

        # List all companies
        res = self.client.get(reverse('company-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get('results', res.data)
        self.assertEqual(len(results), 3)

        # Search exact
        res_amz = self.client.get(reverse('company-list') + '?search=Amazon')
        results_amz = res_amz.data.get('results', res_amz.data)
        self.assertEqual(len(results_amz), 1)
        self.assertEqual(results_amz[0]['name'], 'Amazon')

        # Search case-insensitive partial with whitespace
        res_part = self.client.get(reverse('company-list') + '?search=  mic  ')
        results_part = res_part.data.get('results', res_part.data)
        self.assertEqual(len(results_part), 1)
        self.assertEqual(results_part[0]['name'], 'Microsoft')

        # Search non-existent
        res_none = self.client.get(reverse('company-list') + '?search=NonExistentCompany')
        results_none = res_none.data.get('results', res_none.data)
        self.assertEqual(len(results_none), 0)

    def test_problem_sorting_options(self):
        Problem.objects.create(
            title='Median of Two Sorted Arrays', slug='median-arrays',
            difficulty='Hard', question_number=50, frequency=100.0, source_platform='LeetCode'
        )
        Problem.objects.create(
            title='Add Two Numbers', slug='add-two-numbers',
            difficulty='Medium', question_number=20, frequency=50.0, source_platform='LeetCode'
        )
        self.prob1.frequency = 10.0
        self.prob1.save()

        # 1. Hard sorting: Hard first, then Medium, then Easy
        res_hard = self.client.get(reverse('problem-list') + '?sort=hard')
        self.assertEqual(res_hard.status_code, status.HTTP_200_OK)
        diffs_hard = [p['difficulty'] for p in res_hard.data['results']]
        self.assertEqual(diffs_hard[0], 'Hard')
        self.assertEqual(diffs_hard[1], 'Medium')
        self.assertIn('Easy', diffs_hard[2:])

        # 2. Easy sorting: Easy first, then Medium, then Hard
        res_easy = self.client.get(reverse('problem-list') + '?sort=easy')
        diffs_easy = [p['difficulty'] for p in res_easy.data['results']]
        self.assertEqual(diffs_easy[0], 'Easy')
        self.assertEqual(diffs_easy[1], 'Easy')
        self.assertEqual(diffs_easy[2], 'Medium')
        self.assertEqual(diffs_easy[3], 'Hard')

        # 3. Medium sorting: Medium first
        res_med = self.client.get(reverse('problem-list') + '?sort=medium')
        diffs_med = [p['difficulty'] for p in res_med.data['results']]
        self.assertEqual(diffs_med[0], 'Medium')

        # 4. Most Asked (frequency) sorting: highest frequency first
        res_freq = self.client.get(reverse('problem-list') + '?sort=frequency')
        freq_titles = [p['title'] for p in res_freq.data['results']]
        self.assertEqual(freq_titles[0], 'Median of Two Sorted Arrays')
        self.assertEqual(freq_titles[1], 'Add Two Numbers')

        # 5. Question number sorting: 1, 2, 20, 50
        res_num = self.client.get(reverse('problem-list') + '?sort=question_number')
        nums = [p['question_number'] for p in res_num.data['results'] if p.get('question_number')]
        self.assertEqual(nums, sorted(nums))

        # 6. Sorting with search and difficulty filter together
        res_search_filter = self.client.get(reverse('problem-list') + '?search=Two&difficulty=Easy&sort=hard')
        self.assertEqual(len(res_search_filter.data['results']), 1)
        self.assertEqual(res_search_filter.data['results'][0]['title'], 'Two Sum')

