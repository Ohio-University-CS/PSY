"""
Security audit test suite for the canBet Django application.
Run with: python manage.py test canbet_app.test_security_audit --verbosity=2

Covers:
  - Unauthenticated access to protected page views is redirected to login.
  - Canvas user-ID hijacking is blocked (409 when ID already claimed).
  - Canvas user-ID substitution is blocked (403 when ID bound to a different value).
  - Token login with bad credentials returns 401.
  - Deleting an account via GET (not POST) is silently ignored.
"""

from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from canbet_app.models import CanBetUser


def _make_user(username, password='testpass123', bits=1000):
    return CanBetUser.objects.create_user(
        username=username,
        email=f'{username}@ohio.edu',
        password=password,
        bit_balance=bits,
    )


def _one_submission(assignment_id='HW1'):
    return {
        'course_id':     'CS3560',
        'course_name':   'Software Engineering',
        'assignment_id': assignment_id,
        'submitted_at':  '2025-09-01T10:00:00Z',
        'score':         90,
    }


SYNC_URL = '/api/canvas/sync/'


class TestSecurityAudit(TestCase):

    def setUp(self):
        self.client     = Client()
        self.api_client = APIClient()

        self.user = _make_user('secuser')
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    # ------------------------------------------------------------------
    # Protected page views — unauthenticated access must redirect to login
    # ------------------------------------------------------------------
    def test_main_requires_login(self):
        # Normal security: anonymous GET /main/ redirects to login page.
        response = self.client.get('/main/')
        self.assertRedirects(response, '/login/?next=/main/', fetch_redirect_response=False)

    def test_profile_requires_login(self):
        # Normal security: anonymous GET /profile/ redirects to login page.
        response = self.client.get('/profile/')
        self.assertRedirects(response, '/login/?next=/profile/', fetch_redirect_response=False)

    def test_inventory_page_requires_login(self):
        # Normal security: anonymous GET /inventory/ redirects to login page.
        response = self.client.get('/inventory/')
        self.assertRedirects(response, '/login/?next=/inventory/', fetch_redirect_response=False)

    def test_shop_page_requires_login(self):
        # Normal security: anonymous GET /shop/ redirects to login page.
        response = self.client.get('/shop/')
        self.assertRedirects(response, '/login/?next=/shop/', fetch_redirect_response=False)

    # ------------------------------------------------------------------
    # Canvas sync — cross-user canvas_user_id hijacking
    # ------------------------------------------------------------------
    def test_canvas_sync_rejects_already_claimed_canvas_id(self):
        # Error case: canvas_user_id already linked to another account returns 409.
        other = _make_user('otheruser')
        other.canvas_user_id = 'canvas-001'
        other.save(update_fields=['canvas_user_id'])

        payload = {
            'canvas_user_id': 'canvas-001',
            'submissions':    [_one_submission()],
        }
        response = self.api_client.post(SYNC_URL, payload, format='json')
        self.assertEqual(response.status_code, 409)

    def test_canvas_sync_rejects_mismatched_canvas_id(self):
        # Error case: user already bound to one canvas_user_id cannot switch to another (403).
        self.user.canvas_user_id = 'canvas-mine'
        self.user.save(update_fields=['canvas_user_id'])

        payload = {
            'canvas_user_id': 'canvas-different',
            'submissions':    [_one_submission('HW2')],
        }
        response = self.api_client.post(SYNC_URL, payload, format='json')
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Token login — invalid credentials
    # ------------------------------------------------------------------
    def test_token_login_bad_credentials_returns_401(self):
        # Error case: wrong password on /api/token-login/ returns 401.
        anon = APIClient()
        response = anon.post(
            '/api/token-login/',
            {'username': 'secuser', 'password': 'wrongpass'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_token_login_nonexistent_user_returns_401(self):
        # Error case: unknown username returns 401, not 404 (avoids user enumeration).
        anon = APIClient()
        response = anon.post(
            '/api/token-login/',
            {'username': 'ghost', 'password': 'doesnotmatter'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # Account deletion — GET must not delete the account
    # ------------------------------------------------------------------
    def test_delete_account_get_does_not_delete(self):
        # Edge case: GET /delete-account/ must not delete the user (only POST should).
        self.client.force_login(self.user)
        self.client.get('/delete-account/')
        self.assertTrue(CanBetUser.objects.filter(pk=self.user.pk).exists())
