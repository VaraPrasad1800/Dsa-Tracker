from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tracker.models import UserProfile, RefreshToken
from tracker.services.auth_tokens import hash_token
from tracker.authentication import decode_jwt_token, generate_jwt_token
from tracker.tasks import cleanup_expired_tokens

User = get_user_model()


class JwtRevocationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='jwt_user',
            email='jwt_user@example.com',
            password='Password123!'
        )
        UserProfile.objects.create(user=self.user, is_email_verified=True)
        self.client = APIClient()

    def test_login_creates_refresh_token_record(self):
        res = self.client.post('/api/auth/login/', {
            'username': 'jwt_user',
            'password': 'Password123!'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        refresh_token = res.data['refresh_token']
        self.assertTrue(refresh_token)

        token_hash = hash_token(refresh_token)
        record = RefreshToken.objects.filter(token_hash=token_hash).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.user, self.user)
        self.assertFalse(record.revoked)
        self.assertIsNone(record.revoked_at)

    def test_refresh_with_valid_token_rotates_and_revokes_old(self):
        # 1. Login
        res_login = self.client.post('/api/auth/login/', {
            'username': 'jwt_user',
            'password': 'Password123!'
        }, format='json')
        old_refresh = res_login.data['refresh_token']
        old_hash = hash_token(old_refresh)

        # 2. Refresh
        res_refresh = self.client.post('/api/auth/refresh-token/', {
            'refresh_token': old_refresh
        }, format='json')
        self.assertEqual(res_refresh.status_code, status.HTTP_200_OK)
        new_refresh = res_refresh.data['refresh_token']
        new_hash = hash_token(new_refresh)
        self.assertNotEqual(old_refresh, new_refresh)

        # 3. Old token should be marked revoked
        old_record = RefreshToken.objects.get(token_hash=old_hash)
        self.assertTrue(old_record.revoked)
        self.assertIsNotNone(old_record.revoked_at)

        # 4. New token should be active
        new_record = RefreshToken.objects.get(token_hash=new_hash)
        self.assertFalse(new_record.revoked)

    def test_refresh_with_revoked_token_fails_with_401(self):
        # 1. Login
        res_login = self.client.post('/api/auth/login/', {
            'username': 'jwt_user',
            'password': 'Password123!'
        }, format='json')
        refresh = res_login.data['refresh_token']
        token_hash = hash_token(refresh)

        # 2. Manually revoke or logout
        record = RefreshToken.objects.get(token_hash=token_hash)
        record.revoked = True
        record.revoked_at = timezone.now()
        record.save()

        # 3. Attempt refresh
        res = self.client.post('/api/auth/refresh-token/', {
            'refresh_token': refresh
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('revoked', res.data.get('error', '').lower())

    def test_logout_revokes_token(self):
        # 1. Login
        res_login = self.client.post('/api/auth/login/', {
            'username': 'jwt_user',
            'password': 'Password123!'
        }, format='json')
        refresh = res_login.data['refresh_token']
        token_hash = hash_token(refresh)

        # 2. Call logout
        res_logout = self.client.post('/api/auth/logout/', {
            'refresh_token': refresh
        }, format='json')
        self.assertEqual(res_logout.status_code, status.HTTP_200_OK)
        self.assertEqual(res_logout.data.get('message'), 'Logged out successfully.')

        # 3. Verify record in DB is revoked
        record = RefreshToken.objects.get(token_hash=token_hash)
        self.assertTrue(record.revoked)
        self.assertIsNotNone(record.revoked_at)

        # 4. Refresh token should no longer work
        res_refresh = self.client.post('/api/auth/refresh-token/', {
            'refresh_token': refresh
        }, format='json')
        self.assertEqual(res_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_expires_in_one_hour(self):
        token = generate_jwt_token(self.user, token_type='access')
        payload = decode_jwt_token(token)
        diff_seconds = payload['exp'] - payload['iat']
        self.assertEqual(diff_seconds, 3600)

    def test_cleanup_expired_tokens_task(self):
        # Create an expired token from 35 days ago
        old_time = timezone.now() - timedelta(days=35)
        expired_sub = RefreshToken.objects.create(
            user=self.user,
            token_hash='expired_hash_123',
            expires_at=old_time,
            revoked=True,
            revoked_at=old_time,
        )

        # Create an active fresh token
        active_sub = RefreshToken.objects.create(
            user=self.user,
            token_hash='active_hash_456',
            expires_at=timezone.now() + timedelta(days=7),
            revoked=False,
        )

        result = cleanup_expired_tokens()
        self.assertIn('Cleaned up 1', result)
        self.assertFalse(RefreshToken.objects.filter(token_hash='expired_hash_123').exists())
        self.assertTrue(RefreshToken.objects.filter(token_hash='active_hash_456').exists())
