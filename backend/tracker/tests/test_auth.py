"""Tests for the authentication overhaul and new enhanced endpoints."""
import re
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from tracker.models import Problem, Tag, Company, UserProfile, UserProblemProgress
from tracker.authentication import generate_jwt_token
from tracker.services.email_service import send_verification_email

User = get_user_model()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_signup_verification_email_and_login_gate(self):
        # 1. Sign up
        res = self.client.post(reverse('auth-signup'), {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='alice')
        self.assertTrue(user.is_active)

        # 2. A verification email is queued with the right link format
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('verify-email', body)
        token_match = re.search(r'verify-email/?\?token=([\w-]+)', body)
        self.assertIsNotNone(token_match)
        token = token_match.group(1)

        # 3. Login is blocked until email verified
        res_login = self.client.post(reverse('auth-login'), {
            'username': 'alice', 'password': 'StrongPass123!'
        }, format='json')
        self.assertEqual(res_login.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Verify email with the token
        res_verify = self.client.post(reverse('auth-verify-email'), {
            'token': token
        }, format='json')
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        profile = user.profile
        self.assertTrue(profile.is_email_verified)

        # 5. Token is single-use
        res_reuse = self.client.post(reverse('auth-verify-email'), {'token': token}, format='json')
        self.assertEqual(res_reuse.status_code, status.HTTP_400_BAD_REQUEST)

        # 6. Now login returns the token pair
        res_login2 = self.client.post(reverse('auth-login'), {
            'username': 'alice', 'password': 'StrongPass123!'
        }, format='json')
        self.assertEqual(res_login2.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', res_login2.data)
        self.assertIn('refresh_token', res_login2.data)

        # 7. Access token authenticates a protected endpoint
        token = res_login2.data['access_token']
        res_prot = self.client.get(reverse('analytics-dashboard'),
                                   HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res_prot.status_code, status.HTTP_200_OK)

        # 8. Refresh token issues a new pair
        res_refresh = self.client.post(reverse('auth-refresh-token'), {
            'refresh_token': res_login2.data['refresh_token']
        }, format='json')
        self.assertEqual(res_refresh.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', res_refresh.data)
        self.assertIn('refresh_token', res_refresh.data)

    def test_forgot_and_reset_password(self):
        u = User.objects.create_user(username='bob', email='bob@example.com', password='OldPass123!')
        UserProfile.objects.create(user=u, is_email_verified=True)

        # Anti-enumeration: unknown email still 200
        res_unknown = self.client.post(reverse('auth-forgot-password'), {
            'email': 'nobody@example.com'
        }, format='json')
        self.assertEqual(res_unknown.status_code, status.HTTP_200_OK)

        res = self.client.post(reverse('auth-forgot-password'), {
            'email': 'bob@example.com'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        token_match = re.search(r'reset-password/?\?token=([\w-]+)', body)
        self.assertIsNotNone(token_match)
        reset_token = token_match.group(1)

        # Reset with wrong/new password mismatch handled by view validation
        res_reset = self.client.post(reverse('auth-reset-password'), {
            'token': reset_token,
            'new_password': 'BrandNewPass456!',
        }, format='json')
        self.assertEqual(res_reset.status_code, status.HTTP_200_OK)

        # Old password no longer works, new one does
        u.refresh_from_db()
        self.assertTrue(u.check_password('BrandNewPass456!'))

        # Token is single-use now
        res_reset2 = self.client.post(reverse('auth-reset-password'), {
            'token': reset_token, 'new_password': 'AnotherPass789!',
        }, format='json')
        self.assertEqual(res_reset2.status_code, status.HTTP_400_BAD_REQUEST)


class EnhancedProblemsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='carol', password='password')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {generate_jwt_token(self.user)}'}

        self.tag = Tag.objects.create(name='Array', slug='array', color='#3b82f6', category='data_structure')
        self.comp = Company.objects.create(name='Google', slug='google')

        self.p1 = Problem.objects.create(
            title='Two Sum', slug='two-sum', difficulty='Easy',
            leetcode_id=1, is_premium=False, frequency=90, source_platform='LeetCode'
        )
        self.p1.tags.add(self.tag)
        self.p1.companies.add(self.comp)

        self.p2 = Problem.objects.create(
            title='Alien Dictionary', slug='alien-dictionary', difficulty='Hard',
            leetcode_id=269, is_premium=True, frequency=40,
            source_platform='LeetCode', source_url='https://leetcode.com/problems/alien-dictionary'
        )
        self.p2.tags.add(self.tag)
        self.p2.companies.add(self.comp)

    def test_multi_select_difficulty_and_sort(self):
        res = self.client.get(reverse('problem-list') + '?difficulty=Easy,Hard&sort=frequency')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [r['title'] for r in res.data['results']]
        self.assertEqual(titles, ['Two Sum', 'Alien Dictionary'])  # sorted by -frequency

    def test_random_mode(self):
        res = self.client.get(reverse('problem-list') + '?sort=random')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 2)

    def test_company_drill_endpoint(self):
        res = self.client.get(reverse('problem-by-company', kwargs={'company_id': 'google'}) + '?difficulty=hard')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['slug'], 'alien-dictionary')
        self.assertEqual(res.data['company']['slug'], 'google')

    def test_smart_leetcode_linking(self):
        res = self.client.get(reverse('problem-detail', kwargs={'pk': self.p1.id}))
        # Free problem -> leetcode.com/problems/slug
        self.assertEqual(res.data['leetcode_url'], 'https://leetcode.com/problems/two-sum/')
        # Internal solution API endpoint
        self.assertEqual(res.data['solution_api_url'], f'/api/problems/{self.p1.id}/solution/')

        res2 = self.client.get(reverse('problem-detail', kwargs={'pk': self.p2.id}))
        # Premium problem ALSO -> leetcode.com/problems/slug (never leetcode.ca)
        self.assertEqual(res2.data['leetcode_url'], 'https://leetcode.com/problems/alien-dictionary/')
        # Internal solution API endpoint
        self.assertEqual(res2.data['solution_api_url'], f'/api/problems/{self.p2.id}/solution/')

    def test_company_list_includes_solved_count(self):
        self.client.post(reverse('user-progress-create'), {
            'problem_id': str(self.p1.id), 'status': 'SOLVED'
        }, format='json', **self.auth)
        res = self.client.get(reverse('company-list'), **self.auth)
        google = next(c for c in res.data if c['slug'] == 'google')
        self.assertEqual(google['problem_count'], 2)
        self.assertEqual(google['user_progress']['solved'], 1)

    def test_company_list_anonymous_has_zero_solved(self):
        res = self.client.get(reverse('company-list'))
        google = next(c for c in res.data if c['slug'] == 'google')
        self.assertEqual(google['user_progress']['solved'], 0)

    def test_bookmark_toggle_and_list(self):
        res = self.client.post(reverse('bookmark-toggle'), {
            'problem_id': str(self.p1.id)
        }, format='json', **self.auth)
        self.assertEqual(res.data['bookmarked'], True)

        res_list = self.client.get(reverse('bookmark-list'), **self.auth)
        self.assertEqual(len(res_list.data), 1)
        self.assertEqual(res_list.data[0]['slug'], 'two-sum')
        self.assertTrue(res_list.data[0]['is_bookmarked'])

        # Toggle off
        res2 = self.client.post(reverse('bookmark-toggle'), {
            'problem_id': str(self.p1.id)
        }, format='json', **self.auth)
        self.assertEqual(res2.data['bookmarked'], False)

    def test_analytics_dashboard(self):
        self.client.post(reverse('user-progress-create'), {
            'problem_id': str(self.p1.id), 'status': 'SOLVED'
        }, format='json', **self.auth)
        res = self.client.get(reverse('analytics-dashboard'), **self.auth)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_solved'], 1)
        self.assertIn('placement_readiness', res.data)
        self.assertIn('solved_by_company', res.data)

    def test_protected_endpoint_rejects_anonymous(self):
        res = self.client.get(reverse('analytics-dashboard'))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)