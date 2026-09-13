from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tracker.models import Problem, Tag, Company, UserProblemProgress, ReviewHistory, InterviewSession, Challenge

User = get_user_model()

class CoreE2EFeaturesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_dsa_user', email='dsa@example.com', password='password123')
        self.tag = Tag.objects.create(name='Dynamic Programming', slug='dynamic-programming')
        self.company = Company.objects.create(name='Google', slug='google')
        self.problem = Problem.objects.create(
            title='Climbing Stairs',
            slug='climbing-stairs',
            difficulty='Easy',
            question_number=70,
            description='You are climbing a staircase.',
            examples=[{'input': 'n = 2', 'output': '2'}],
            constraints=['1 <= n <= 45'],
            leetcode_id=70,
        )
        self.problem.tags.add(self.tag)
        self.problem.companies.add(self.company)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_all_11_core_features_end_to_end(self):
        # 1. Problem Search & List
        res = self.client.get('/api/problems/?search=Climbing')
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data['results']), 1)

        # 2. Companies List
        res = self.client.get('/api/problems/companies/')
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 1)

        # 3. Problem Detail (structured statement)
        res = self.client.get(f'/api/problems/{self.problem.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['title'], 'Climbing Stairs')
        self.assertIn('examples', res.data)
        self.assertIn('constraints', res.data)
        self.assertIn('leetcode_url', res.data)

        # 4. User Progress & Notes
        res = self.client.post('/api/user-progress/', {
            'problem_id': str(self.problem.id),
            'status': 'SOLVED',
            'notes': 'Used Fibonacci pattern',
        })
        self.assertIn(res.status_code, [200, 201])
        self.assertTrue(UserProblemProgress.objects.filter(user=self.user, problem=self.problem, status='SOLVED').exists())

        # 5. Leitner Spaced Repetition
        res = self.client.get('/api/user-progress/due-today/')
        self.assertEqual(res.status_code, 200)

        # 6. Analytics Dashboard
        res = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(res.status_code, 200)

        # 7. Study Plans
        res = self.client.post('/api/study-plans/generate/', {
            'days': 7,
            'problems_per_day': 2,
        })
        self.assertIn(res.status_code, [200, 201])

        # 8. Challenges
        res = self.client.get('/api/challenges/')
        self.assertEqual(res.status_code, 200)

        # 9. Interview Mode Flow
        res_start = self.client.post('/api/interview-sessions/', {
            'duration_minutes': 45,
            'num_problems': 1,
            'difficulty': 'Easy',
        })
        self.assertEqual(res_start.status_code, 201)
        sess_id = res_start.data['id']
        prob_id = res_start.data['interview_problems'][0]['problem']

        # Solve interview problem
        res_solve = self.client.post(f'/api/interview-sessions/{sess_id}/problems/{prob_id}/solve/')
        self.assertEqual(res_solve.status_code, 200)
        self.assertTrue(res_solve.data['solved'])

        # End interview session
        res_end = self.client.post(f'/api/interview-sessions/{sess_id}/end/')
        self.assertEqual(res_end.status_code, 200)
        self.assertEqual(res_end.data['status'], 'COMPLETED')
        self.assertEqual(res_end.data['problems_solved'], 1)

        # 10. Notifications
        res = self.client.get('/api/notifications/')
        self.assertEqual(res.status_code, 200)

        # 11. Bookmarks
        res_bm = self.client.post('/api/bookmarks/toggle/', {'problem_id': str(self.problem.id)})
        self.assertEqual(res_bm.status_code, 200)
        self.assertTrue(res_bm.data['bookmarked'])
