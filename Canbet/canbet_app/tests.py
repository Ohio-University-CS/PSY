"""
Framework : Django TestCase + Django REST Framework APIClient
Run with  : python manage.py test canbet_app.tests --verbosity=2

What do we aim to test with these?
  Models      : CanBetUser, Item, InventoryEntry, CrateOpen, ShopPurchase, CanvasSubmission
  API views   : /api/me/, /api/crate/open/, /api/shop/buy/,
                /api/inventory/, /api/leaderboard/, /api/recent-opens/
  Page views  : home, about, login, logout, register, main, inventory,
                leaderboard, profile, settings, shop, crate
  Business    : bit deduction, rank calculation, loot-table weighting,
                duplicate-purchase guard, Canvas sync helpers
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from django.test import override_settings
import json

from canbet_app.models import (
    CanBetUser, Item, InventoryEntry, CrateOpen, ShopPurchase, CanvasSubmission
)


def make_user(username='testuser', password='testpass123', bits=1000, email=None):
    # Create a CanBetUser for use in tests.
    email = email or f'{username}@ohio.edu'
    user = CanBetUser.objects.create_user(
        username=username, password=password,
        email=email, bit_balance=bits
    )
    return user

def make_item(name='Test Item', rarity='COMMON', collection='SPOOKY',
              shop_price=50, crate_weight=10):
    # Create an Item for use in tests.
    return Item.objects.create(
        name=name, rarity=rarity, collection=collection,
        shop_price=shop_price, crate_weight=crate_weight,
        sprite_path=f'sprites/Items/Spooky_collection/{name}.png'
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  1. USER — creation and defaults
#  Author: Jimmy
class TestCanBetUserCreation(TestCase):

    def test_normal_user_creation(self):
        # Normal case: user is created with correct default values.
        user = make_user(username='alice', bits=1000)
        self.assertEqual(user.username, 'alice')
        self.assertEqual(user.bit_balance, 1000)
        self.assertEqual(user.crates_opened, 0)

    def test_user_default_bit_balance(self):
        # Edge case: user created without specifying bits gets default 1000.
        user = CanBetUser.objects.create_user(username='bob', password='pass')
        self.assertEqual(user.bit_balance, 1000)

    def test_duplicate_username_raises(self):
        # Error case: creating two users with the same username raises an error.
        make_user(username='dupuser')
        with self.assertRaises(Exception):
            make_user(username='dupuser')


# ═══════════════════════════════════════════════════════════════════════════════
#  2. USER — rank calculation
#  Author: Jimmy
class TestUserRank(TestCase):

    def test_rank_single_user(self):
        # Normal case: only user in the DB should be rank 1.
        user = make_user(bits=500)
        self.assertEqual(user.rank, 1)

    def test_rank_ordering(self):
        # Normal case: user with highest bits is rank 1, second highest is rank 2.
        rich  = make_user('rich',  bits=9000)
        poor  = make_user('poor',  bits=100)
        mid   = make_user('mid',   bits=500)
        self.assertEqual(rich.rank, 1)
        self.assertEqual(mid.rank,  2)
        self.assertEqual(poor.rank, 3)

    def test_rank_updates_after_bit_change(self):
        # Edge case: rank recalculates live when bits change.
        user_a = make_user('a', bits=1000)
        user_b = make_user('b', bits=500)
        self.assertEqual(user_a.rank, 1)
        # Give user_b more bits
        user_b.bit_balance = 2000
        user_b.save()
        self.assertEqual(user_b.rank, 1)
        self.assertEqual(user_a.rank, 2)

    def test_rank_tie_both_get_same_rank(self):
        # Edge case: users with identical bits share a rank.
        user_a = make_user('ta', bits=500)
        user_b = make_user('tb', bits=500)
        self.assertEqual(user_a.rank, user_b.rank)


# ═══════════════════════════════════════════════════════════════════════════════
#  3. ITEM MODEL — creation and validation
#  Author: Jimmy
class TestItemModel(TestCase):

    def test_normal_item_creation(self):
        # Normal case: item saves correctly with all fields.
        item = make_item(name='Vampire', rarity='RARE', shop_price=120, crate_weight=20)
        self.assertEqual(item.name, 'Vampire')
        self.assertEqual(item.rarity, 'RARE')
        self.assertEqual(item.shop_price, 120)

    def test_item_str_representation(self):
        #Normal case: __str__ returns name and rarity.
        item = make_item(name='Cthulhu', rarity='EPIC')
        self.assertIn('Cthulhu', str(item))
        self.assertIn('EPIC', str(item))

    def test_duplicate_item_name_raises(self):
        #Error case: two items with the same name should raise an integrity error.
        make_item(name='UniqueItem')
        with self.assertRaises(Exception):
            make_item(name='UniqueItem')

    def test_item_not_for_sale_has_zero_price(self):
        #Edge case: item with shop_price=0 is valid and means not for sale.
        item = Item.objects.create(
            name='CrateOnly', rarity='COMMON', collection='SPOOKY',
            shop_price=0, crate_weight=10
        )
        self.assertEqual(item.shop_price, 0)


# ═══════════════════════════════════════════════════════════════════════════════
#  4. INVENTORY MODEL
#  Author: Zane
class TestInventoryEntry(TestCase):

    def setUp(self):
        self.user = make_user()
        self.item = make_item()

    def test_normal_inventory_creation(self):
        # Normal case: inventory entry is created for user and item.
        entry = InventoryEntry.objects.create(user=self.user, item=self.item)
        self.assertEqual(entry.quantity, 1)
        self.assertEqual(entry.user, self.user)

    def test_quantity_increment(self):
        # Normal case: quantity increments correctly for duplicate items.
        entry = InventoryEntry.objects.create(user=self.user, item=self.item, quantity=1)
        entry.quantity += 1
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.quantity, 2)

    def test_duplicate_entry_unique_together_raises(self):
        # Error case: creating two entries for the same user+item raises an error.
        InventoryEntry.objects.create(user=self.user, item=self.item)
        with self.assertRaises(Exception):
            InventoryEntry.objects.create(user=self.user, item=self.item)

    def test_inventory_deleted_with_user(self):
        # Edge case: inventory entries are deleted when the user is deleted (CASCADE).
        InventoryEntry.objects.create(user=self.user, item=self.item)
        self.user.delete()
        self.assertEqual(InventoryEntry.objects.count(), 0)


# ═══════════════════════════════════════════════════════════════════════════════
#  5. SHOP PURCHASE MODEL
#  Author: Christian
class TestShopPurchase(TestCase):

    def setUp(self):
        self.user = make_user(bits=500)
        self.item = make_item(shop_price=100)

    def test_purchase_logs_correctly(self):
        # Normal case: purchase record saves user, item, and correct cost.
        purchase = ShopPurchase.objects.create(
            user=self.user, item=self.item, bits_spent=self.item.shop_price
        )
        self.assertEqual(purchase.bits_spent, 100)
        self.assertEqual(purchase.user, self.user)

    def test_purchase_timestamp_auto_set(self):
        # Normal case: purchased_at is set automatically on creation.
        purchase = ShopPurchase.objects.create(
            user=self.user, item=self.item, bits_spent=100
        )
        self.assertIsNotNone(purchase.purchased_at)

    def test_purchase_deleted_with_user(self):
        # Edge case: purchase records cascade-delete with user.
        ShopPurchase.objects.create(user=self.user, item=self.item, bits_spent=100)
        self.user.delete()
        self.assertEqual(ShopPurchase.objects.count(), 0)


# ═══════════════════════════════════════════════════════════════════════════════
#  6. CRATE OPEN MODEL
#  Author: Evan
class TestCrateOpen(TestCase):

    def setUp(self):
        self.user = make_user()
        self.item = make_item()

    def test_crate_open_logged(self):
        # Normal case: crate open is recorded with correct fields.
        record = CrateOpen.objects.create(
            user=self.user, crate_type='SPOOKY', item_won=self.item, bits_spent=200
        )
        self.assertEqual(record.crate_type, 'SPOOKY')
        self.assertEqual(record.bits_spent, 200)
        self.assertEqual(record.item_won, self.item)

    def test_crate_open_null_item(self):
        # Edge case: item_won can be null (SET_NULL on delete) without error.
        record = CrateOpen.objects.create(
            user=self.user, crate_type='SPOOKY', item_won=None, bits_spent=200
        )
        self.assertIsNone(record.item_won)

    def test_crate_open_ordering(self):
        # Normal case: most recent open appears first.
        CrateOpen.objects.create(user=self.user, crate_type='SPOOKY', bits_spent=200)
        CrateOpen.objects.create(user=self.user, crate_type='SPOOKY', bits_spent=200)
        opens = CrateOpen.objects.all()
        self.assertGreaterEqual(opens[0].opened_at, opens[1].opened_at)

# ═══════════════════════════════════════════════════════════════════════════════
#  7. PAGE VIEW — public pages (home, about)
#  Author: Ethan
class TestPublicPageViews(TestCase):

    def setUp(self):
        self.client = Client()

    def test_home_page_returns_200(self):
        # Normal case: home page loads for anonymous user.
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_about_page_returns_200(self):
        # Normal case: about page loads for anonymous user.
        response = self.client.get('/about/')
        self.assertEqual(response.status_code, 200)

    def test_home_uses_correct_template(self):
        # Normal case: home view renders home.html template.
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')

    def test_nonexistent_page_returns_404(self):
        # Error case: random URL returns 404.
        response = self.client.get('/doesnotexist/')
        self.assertEqual(response.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════════
#  8. PAGE VIEW — login
#  Author: Ethan
class TestLoginView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='loginuser', password='correct123')

    def test_login_page_get(self):
        # Normal case: GET /login/ returns the login form.
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_with_valid_credentials(self):
        # Normal case: valid username + password logs user in and redirects to main.
        response = self.client.post('/login/', {
            'email': 'loginuser', 'password': 'correct123'
        })
        self.assertRedirects(response, '/main/')

    def test_login_with_wrong_password(self):
        # Error case: wrong password stays on login page with error.
        response = self.client.post('/login/', {
            'email': 'loginuser', 'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)

    def test_login_already_authenticated_redirects(self):
        # Edge case: logged-in user hitting /login/ is redirected to main.
        self.client.force_login(self.user)
        response = self.client.get('/login/')
        self.assertRedirects(response, '/main/')


# ═══════════════════════════════════════════════════════════════════════════════
#  9. PAGE VIEW — logout
#  Author: Ethan
class TestLogoutView(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client = Client()
        self.client.force_login(self.user)

    def test_logout_redirects_to_login(self):
        # Normal case: logout redirects to /login/.
        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/')

    def test_logout_clears_session(self):
        # Normal case: after logout, /main/ redirects to login.
        self.client.get('/logout/')
        response = self.client.get('/main/')
        self.assertRedirects(response, '/login/?next=/main/')

    def test_logout_unauthenticated_still_redirects(self):
        # Edge case: logging out when not logged in still redirects cleanly.
        self.client.logout()
        response = self.client.get('/logout/')
        self.assertEqual(response.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
#  10. PAGE VIEW — protected pages redirect when not logged in
#  Author: Ethan
class TestAuthProtectedViews(TestCase):

    def setUp(self):
        self.client = Client()

    def test_main_redirects_anonymous(self):
        # Normal case: /main/ redirects anonymous user to login.
        response = self.client.get('/main/')
        self.assertRedirects(response, '/login/?next=/main/')

    def test_inventory_redirects_anonymous(self):
        # Normal case: /inventory/ redirects anonymous user.
        response = self.client.get('/inventory/')
        self.assertRedirects(response, '/login/?next=/inventory/')

    def test_shop_redirects_anonymous(self):
        # Normal case: /shop/ redirects anonymous user.
        response = self.client.get('/shop/')
        self.assertRedirects(response, '/login/?next=/shop/')

    def test_protected_pages_load_when_logged_in(self):
        # Edge case: all protected pages return 200 when authenticated.
        user = make_user()
        self.client.force_login(user)
        for url in ['/main/', '/inventory/', '/leaderboard/', '/profile/', '/settings/', '/shop/', '/crate/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, msg=f'{url} returned {response.status_code}')


# ═══════════════════════════════════════════════════════════════════════════════
#  11. PAGE VIEW — register
#  Author: Jimmy
class TestRegisterView(TestCase):

    def setUp(self):
        self.client = Client()

    def test_register_get_returns_form(self):
        # Normal case: GET /register/ shows the registration form.
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_redirects(self):
        # Normal case: valid registration creates user and redirects to main.
        response = self.client.post('/register/', {
            'username': 'newplayer',
            'email':    'newplayer@ohio.edu',
            'password': 'StrongPass1!',
            'confirm':  'StrongPass1!',
        })
        self.assertRedirects(response, '/main/')
        self.assertTrue(CanBetUser.objects.filter(username='newplayer').exists())

    def test_register_mismatched_passwords(self):
        # Error case: mismatched passwords shows error, no user created.
        response = self.client.post('/register/', {
            'username': 'badpass',
            'email':    'badpass@ohio.edu',
            'password': 'abc',
            'confirm':  'xyz',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertFalse(CanBetUser.objects.filter(username='badpass').exists())

    def test_register_duplicate_username(self):
        # Error case: duplicate username shows error.
        make_user(username='taken')
        response = self.client.post('/register/', {
            'username': 'taken',
            'email':    'other@ohio.edu',
            'password': 'pass123',
            'confirm':  'pass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)


# ═══════════════════════════════════════════════════════════════════════════════
#  12. API — /api/me/
#  Author: Ethan
class TestApiMe(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(bits=1500)

    def test_me_returns_correct_data(self):
        # Normal case: returns username, bit_balance, crates_opened, rank.
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['bit_balance'], 1500)

    def test_me_unauthenticated_returns_403(self):
        # Error case: unauthenticated request is rejected.
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 403)

    def test_me_includes_rank(self):
        # Edge case: rank field is included and is a positive integer.
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/me/')
        self.assertIn('rank', response.data)
        self.assertGreaterEqual(response.data['rank'], 1)


# ═══════════════════════════════════════════════════════════════════════════════
#  13. API — /api/shop/buy/
#  Author: Christian
class TestApiBuyItem(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(bits=500)
        self.item = make_item(name='BuyableItem', shop_price=100)
        self.client.force_authenticate(user=self.user)

    def test_buy_item_success(self):
        # Normal case: buying an item deducts bits and returns new balance.
        response = self.client.post('/api/shop/buy/', {'item_id': self.item.id}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bit_balance, 400)

    def test_buy_item_adds_to_inventory(self):
        # Normal case: purchased item appears in user's inventory.
        self.client.post('/api/shop/buy/', {'item_id': self.item.id}, format='json')
        self.assertTrue(InventoryEntry.objects.filter(user=self.user, item=self.item).exists())

    def test_buy_item_insufficient_bits(self):
        # Error case: user with too few bits gets 402.
        poor_user = make_user('poor', bits=10)
        self.client.force_authenticate(user=poor_user)
        response = self.client.post('/api/shop/buy/', {'item_id': self.item.id}, format='json')
        self.assertEqual(response.status_code, 402)

    def test_buy_item_already_owned(self):
        # Error case: buying an item already in inventory returns 409.
        InventoryEntry.objects.create(user=self.user, item=self.item)
        response = self.client.post('/api/shop/buy/', {'item_id': self.item.id}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_buy_item_not_for_sale(self):
        # Edge case: item with shop_price=0 returns 400.
        free_item = make_item(name='FreeItem', shop_price=0)
        response = self.client.post('/api/shop/buy/', {'item_id': free_item.id}, format='json')
        self.assertEqual(response.status_code, 400)


# ═══════════════════════════════════════════════════════════════════════════════
#  14. API — /api/crate/open/
#  Author: Jimmy
class TestApiOpenCrate(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(bits=1000)
        # Populate SPOOKY pool
        make_item(name='CrateCommon', rarity='COMMON', collection='SPOOKY',
                  shop_price=0, crate_weight=100)
        self.client.force_authenticate(user=self.user)

    def test_open_crate_success(self):
        # Normal case: opening a valid crate returns item and deducts 200 bits.
        response = self.client.post('/api/crate/open/', {'crate_type': 'SPOOKY'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('item', response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bit_balance, 800)

    def test_open_crate_increments_crates_opened(self):
        # Normal case: crates_opened counter increments by 1.
        self.client.post('/api/crate/open/', {'crate_type': 'SPOOKY'}, format='json')
        self.user.refresh_from_db()
        self.assertEqual(self.user.crates_opened, 1)

    def test_open_crate_logs_crate_open(self):
        # Normal case: a CrateOpen record is created.
        self.client.post('/api/crate/open/', {'crate_type': 'SPOOKY'}, format='json')
        self.assertEqual(CrateOpen.objects.filter(user=self.user).count(), 1)

    def test_open_crate_insufficient_bits(self):
        # Error case: user with fewer than 200 bits gets 402.
        broke = make_user('broke', bits=50)
        self.client.force_authenticate(user=broke)
        response = self.client.post('/api/crate/open/', {'crate_type': 'SPOOKY'}, format='json')
        self.assertEqual(response.status_code, 402)

    def test_open_crate_unknown_type(self):
        # Error case: invalid crate_type returns 400.
        response = self.client.post('/api/crate/open/', {'crate_type': 'FAKE'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_open_crate_empty_pool(self):
        # Edge case: crate with no items in DB returns 503.
        response = self.client.post('/api/crate/open/', {'crate_type': 'SPACE'}, format='json')
        self.assertEqual(response.status_code, 503)


# ═══════════════════════════════════════════════════════════════════════════════
#  15. API — /api/inventory/
#  Author: Christian
class TestApiInventory(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def test_empty_inventory_returns_empty_list(self):
        # Normal case: user with no items gets an empty list.
        response = self.client.get('/api/inventory/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_inventory_shows_owned_items(self):
        # Normal case: items in inventory appear in response.
        item = make_item(name='OwnedItem')
        InventoryEntry.objects.create(user=self.user, item=item)
        response = self.client.get('/api/inventory/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'OwnedItem')

    def test_inventory_unauthenticated_returns_403(self):
        # Error case: unauthenticated request is rejected.
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/inventory/')
        self.assertEqual(response.status_code, 403)

    def test_inventory_shows_quantity(self):
        # Edge case: quantity field is present and accurate.
        item = make_item(name='StackedItem')
        InventoryEntry.objects.create(user=self.user, item=item, quantity=3)
        response = self.client.get('/api/inventory/')
        self.assertEqual(response.data[0]['quantity'], 3)


# ═══════════════════════════════════════════════════════════════════════════════
#  16. API — /api/leaderboard/
#  Author: Zane
class TestApiLeaderboard(TestCase):

    def test_leaderboard_is_sorted_by_bits(self):
        # Normal case: players are returned highest bits first.
        make_user('low',  bits=100)
        make_user('high', bits=9000)
        make_user('mid',  bits=500)
        client = APIClient()
        response = client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, 200)
        balances = [p['bit_balance'] for p in response.data]
        self.assertEqual(balances, sorted(balances, reverse=True))

    def test_leaderboard_rank_field_sequential(self):
        # Normal case: rank field increments from 1.
        make_user('p1', bits=1000)
        make_user('p2', bits=500)
        client = APIClient()
        response = client.get('/api/leaderboard/')
        ranks = [p['rank'] for p in response.data]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_leaderboard_empty_returns_empty_list(self):
        # Edge case: no users returns empty list, not an error.
        client = APIClient()
        response = client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_leaderboard_capped_at_50(self):
        # Edge case: leaderboard never returns more than 50 players.
        for i in range(60):
            make_user(f'player{i}', bits=i * 10)
        client = APIClient()
        response = client.get('/api/leaderboard/')
        self.assertLessEqual(len(response.data), 50)


# ═══════════════════════════════════════════════════════════════════════════════
#  17. API — /api/recent-opens/
#  Author: Zane
class TestApiRecentOpens(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user   = make_user()
        self.item   = make_item()

    def test_recent_opens_empty(self):
        # Normal case: no opens returns empty list.
        response = self.client.get('/api/recent-opens/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_recent_opens_shows_latest_first(self):
        # Normal case: most recent open is first in list.
        CrateOpen.objects.create(user=self.user, crate_type='SPOOKY', item_won=self.item, bits_spent=200)
        CrateOpen.objects.create(user=self.user, crate_type='SPOOKY', item_won=self.item, bits_spent=200)
        response = self.client.get('/api/recent-opens/')
        times = [r['opened_at'] for r in response.data]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_recent_opens_capped_at_20(self):
        # Edge case: never returns more than 20 records.
        for _ in range(25):
            CrateOpen.objects.create(user=self.user, crate_type='SPOOKY',
                                     item_won=self.item, bits_spent=200)
        response = self.client.get('/api/recent-opens/')
        self.assertLessEqual(len(response.data), 20)

    def test_recent_opens_handles_null_item(self):
        # Edge case: open with null item_won returns '?' without crashing.
        CrateOpen.objects.create(user=self.user, crate_type='SPOOKY',
                                 item_won=None, bits_spent=200)
        response = self.client.get('/api/recent-opens/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['item'], '?')


# ═══════════════════════════════════════════════════════════════════════════════
#  18. BIT BALANCE INTEGRITY
#  Author: Christian
class TestBitBalanceIntegrity(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_bits_not_deducted_on_failed_buy(self):
        # Error case: bits are NOT deducted if purchase fails (already owned).
        user = make_user(bits=500)
        item = make_item(shop_price=100)
        InventoryEntry.objects.create(user=user, item=item)
        self.client.force_authenticate(user=user)
        self.client.post('/api/shop/buy/', {'item_id': item.id}, format='json')
        user.refresh_from_db()
        self.assertEqual(user.bit_balance, 500)  # unchanged

    def test_bits_not_deducted_on_empty_crate(self):
        # Error case: bits are NOT deducted when crate pool is empty.
        user = make_user(bits=1000)
        self.client.force_authenticate(user=user)
        self.client.post('/api/crate/open/', {'crate_type': 'SPACE'}, format='json')
        user.refresh_from_db()
        self.assertEqual(user.bit_balance, 1000)  # unchanged

    def test_multiple_purchases_each_deduct_correctly(self):
        # Normal case: buying two different items deducts both prices.
        user = make_user(bits=500)
        item1 = make_item(name='Item1', shop_price=100)
        item2 = make_item(name='Item2', shop_price=150)
        self.client.force_authenticate(user=user)
        self.client.post('/api/shop/buy/', {'item_id': item1.id}, format='json')
        self.client.post('/api/shop/buy/', {'item_id': item2.id}, format='json')
        user.refresh_from_db()
        self.assertEqual(user.bit_balance, 250)


# ═══════════════════════════════════════════════════════════════════════════════
#  19. CANVAS SUBMISSION MODEL
#  Author: Zane
class TestCanvasSubmission(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_submission_creation(self):
        # Normal case: submission record saves with all required fields.
        sub = CanvasSubmission.objects.create(
            user=self.user, course_name='CS101', course_id='111',
            assignment_id='55', score=95.0
        )
        self.assertEqual(sub.course_name, 'CS101')
        self.assertEqual(sub.score, 95.0)

    def test_submission_null_score_allowed(self):
        # Edge case: score can be null (ungraded assignment).
        sub = CanvasSubmission.objects.create(
            user=self.user, course_name='CS101', course_id='111',
            assignment_id='56', score=None
        )
        self.assertIsNone(sub.score)

    def test_submission_unique_together(self):
        # Error case: duplicate user+course+assignment raises integrity error.
        CanvasSubmission.objects.create(
            user=self.user, course_name='CS101', course_id='111', assignment_id='55'
        )
        with self.assertRaises(Exception):
            CanvasSubmission.objects.create(
                user=self.user, course_name='CS101', course_id='111', assignment_id='55'
            )

    def test_submission_deleted_with_user(self):
        # Edge case: submissions cascade-delete when user is deleted.
        CanvasSubmission.objects.create(
            user=self.user, course_name='CS101', course_id='111', assignment_id='55'
        )
        self.user.delete()
        self.assertEqual(CanvasSubmission.objects.count(), 0)


# ═══════════════════════════════════════════════════════════════════════════════
#  20. LOOT TABLE — weighted random roll distribution
#  Author: Evan
class TestLootTableWeighting(TestCase):

    def setUp(self):
        # Legendary weight=1, Common weight=99 — common should win almost always
        self.legendary = make_item('LegendaryItem', rarity='LEGENDARY',
                                   collection='SPOOKY', crate_weight=1)
        self.common    = make_item('CommonItem',    rarity='COMMON',
                                   collection='SPOOKY', crate_weight=99)

    def test_high_weight_item_wins_more(self):
        # Normal case: common item (weight 99) wins far more often than legendary (weight 1).
        import random
        pool    = [self.legendary, self.common]
        weights = [i.crate_weight for i in pool]
        wins = {'LegendaryItem': 0, 'CommonItem': 0}
        for _ in range(500):
            [won] = random.choices(pool, weights=weights, k=1)
            wins[won.name] += 1
        self.assertGreater(wins['CommonItem'], wins['LegendaryItem'])

    def test_single_item_pool_always_returns_that_item(self):
        # Edge case: pool of one item always returns that item.
        import random
        pool    = [self.legendary]
        weights = [self.legendary.crate_weight]
        for _ in range(10):
            [won] = random.choices(pool, weights=weights, k=1)
            self.assertEqual(won.name, 'LegendaryItem')

    def test_zero_weight_items_never_roll(self):
        # Edge case: item with weight=0 should never be selected.
        import random
        zero_item = make_item('ZeroItem', collection='SPOOKY', crate_weight=0)
        pool      = [self.common, zero_item]
        weights   = [i.crate_weight for i in pool]
        for _ in range(100):
            [won] = random.choices(pool, weights=weights, k=1)
            self.assertNotEqual(won.name, 'ZeroItem')


# ═══════════════════════════════════════════════════════════════════════════════
#  21. MAIN DASHBOARD — context data
#  Author: Evan
class TestMainDashboard(TestCase):

    def setUp(self):
        self.user = make_user(bits=1674)
        self.client = Client()
        self.client.force_login(self.user)

    def test_main_page_loads(self):
        # Normal case: main page returns 200 for logged-in user.
        response = self.client.get('/main/')
        self.assertEqual(response.status_code, 200)

    def test_main_context_has_user(self):
        # Normal case: user object is passed in context.
        response = self.client.get('/main/')
        self.assertEqual(response.context['user'], self.user)

    def test_main_context_has_top5(self):
        # Normal case: top5 leaderboard list is in context.
        response = self.client.get('/main/')
        self.assertIn('top5', response.context)

    def test_main_top5_capped_at_5(self):
        # Edge case: top5 never contains more than 5 players even with 10 users.
        for i in range(10):
            make_user(f'extra{i}', bits=i * 100)
        response = self.client.get('/main/')
        self.assertLessEqual(len(response.context['top5']), 5)


# ═══════════════════════════════════════════════════════════════════════════════
#  22. PROFILE VIEW — context data
#  Author: Evan
class TestProfileView(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client = Client()
        self.client.force_login(self.user)

    def test_profile_loads(self):
        # Normal case: profile page returns 200.
        response = self.client.get('/profile/')
        self.assertEqual(response.status_code, 200)

    def test_profile_no_items_shows_none(self):
        # Edge case: best_pull is None when inventory is empty.
        response = self.client.get('/profile/')
        self.assertIsNone(response.context['best_pull'])

    def test_profile_best_pull_is_highest_rarity(self):
        # Normal case: best_pull shows the highest rarity item name.
        common    = make_item('CommonThing',    rarity='COMMON')
        legendary = make_item('LegendaryThing', rarity='LEGENDARY')
        InventoryEntry.objects.create(user=self.user, item=common)
        InventoryEntry.objects.create(user=self.user, item=legendary)
        response = self.client.get('/profile/')
        self.assertEqual(response.context['best_pull'], 'LegendaryThing')

    def test_profile_total_spent_sums_correctly(self):
        # Normal case: total_spent reflects all shop purchases.
        item1 = make_item('S1', shop_price=100)
        item2 = make_item('S2', shop_price=200)
        ShopPurchase.objects.create(user=self.user, item=item1, bits_spent=100)
        ShopPurchase.objects.create(user=self.user, item=item2, bits_spent=200)
        response = self.client.get('/profile/')
        self.assertEqual(response.context['total_spent'], 300)


# ═══════════════════════════════════════════════════════════════════════════════
#  23. SHOP VIEW — context data
#  Author: Christian
class TestShopView(TestCase):

    def setUp(self):
        self.user = make_user(bits=999)
        self.client = Client()
        self.client.force_login(self.user)

    def test_shop_shows_only_purchasable_items(self):
        # Normal case: items with shop_price=0 are excluded from shop.
        make_item('ForSale',   shop_price=50)
        make_item('NotForSale', shop_price=0)
        response = self.client.get('/shop/')
        names = [i.name for i in response.context['items']]
        self.assertIn('ForSale', names)
        self.assertNotIn('NotForSale', names)

    def test_shop_owned_ids_reflect_inventory(self):
        # Normal case: items already owned appear in owned_ids set.
        item = make_item('AlreadyOwned', shop_price=50)
        InventoryEntry.objects.create(user=self.user, item=item)
        response = self.client.get('/shop/')
        self.assertIn(item.id, response.context['owned_ids'])

    def test_shop_empty_when_no_items(self):
        # Edge case: empty item table shows empty list without error.
        response = self.client.get('/shop/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 0)


# ═══════════════════════════════════════════════════════════════════════════════
#  24. LEADERBOARD VIEW — ordering
#  Author: Evan
class TestLeaderboardView(TestCase):

    def setUp(self):
        self.user = make_user('viewer', bits=500)
        self.client = Client()
        self.client.force_login(self.user)

    def test_leaderboard_sorted_descending(self):
        # Normal case: players shown highest bits first.
        make_user('low',  bits=100)
        make_user('high', bits=9999)
        response = self.client.get('/leaderboard/')
        players  = list(response.context['players'])
        balances = [p.bit_balance for p in players]
        self.assertEqual(balances, sorted(balances, reverse=True))

    def test_leaderboard_includes_current_user(self):
        # Normal case: the logged-in user appears somewhere in the list.
        response = self.client.get('/leaderboard/')
        usernames = [p.username for p in response.context['players']]
        self.assertIn('viewer', usernames)

    def test_leaderboard_empty_state(self):
        # Edge case: works correctly with only one user (the viewer).
        response = self.client.get('/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.context['players']), 1)


# ═══════════════════════════════════════════════════════════════════════════════
#  25. CANVAS SYNC — management command logic
#  Author: Zane
class TestCanvasSyncLogic(TestCase):
    """
    Tests the Canvas sync logic without hitting the real Canvas API.
    We mock requests.get so tests are fast and offline-safe.
    """

    def setUp(self):
        self.user = make_user()
        self.user.canvas_user_id = '99999'
        self.user.save()

    @override_settings(CANVAS_TOKEN='fake-token')
    @patch('requests.get')
    def test_sync_awards_bits_for_new_submission(self, mock_get):
        # Normal case: a new on-time submission awards 50 bits.# 
        # Mock course list
        courses_resp = MagicMock()
        courses_resp.status_code = 200
        courses_resp.json.return_value = [{'id': 1, 'name': 'CS101'}]

        # Mock submission list with one on-time submission
        subs_resp = MagicMock()
        subs_resp.status_code = 200
        subs_resp.json.return_value = [{
            'assignment_id': 42,
            'submitted_at':  '2025-09-01T10:00:00Z',
            'score':         90.0
        }]

        mock_get.side_effect = [courses_resp, subs_resp]

        from django.core.management import call_command
        from io import StringIO
        call_command('sync_canvas', '--user', self.user.username, stdout=StringIO())

        self.user.refresh_from_db()
        self.assertEqual(self.user.bit_balance, 1050)  # 1000 default + 50

    @override_settings(CANVAS_TOKEN='fake-token')
    @patch('requests.get')
    def test_sync_no_bits_for_duplicate_submission(self, mock_get):
        # Edge case: re-syncing same submission doesn't award bits twice.# 
        # Pre-create the submission so it already exists
        CanvasSubmission.objects.create(
            user=self.user, course_name='CS101', course_id='1',
            assignment_id='42', submitted_at=timezone.now(), score=90.0
        )

        courses_resp = MagicMock()
        courses_resp.status_code = 200
        courses_resp.json.return_value = [{'id': 1, 'name': 'CS101'}]

        subs_resp = MagicMock()
        subs_resp.status_code = 200
        subs_resp.json.return_value = [{
            'assignment_id': 42,
            'submitted_at':  '2025-09-01T10:00:00Z',
            'score':         90.0
        }]

        mock_get.side_effect = [courses_resp, subs_resp]

        from django.core.management import call_command
        from io import StringIO
        call_command('sync_canvas', '--user', self.user.username, stdout=StringIO())

        self.user.refresh_from_db()
        self.assertEqual(self.user.bit_balance, 1000)  # no change

    @override_settings(CANVAS_TOKEN='fake-token')
    @patch('requests.get')
    def test_sync_no_bits_for_missing_submission_date(self, mock_get):
        # Edge case: submission with no submitted_at date earns no bits.# 
        courses_resp = MagicMock()
        courses_resp.status_code = 200
        courses_resp.json.return_value = [{'id': 1, 'name': 'CS101'}]

        subs_resp = MagicMock()
        subs_resp.status_code = 200
        subs_resp.json.return_value = [{'assignment_id': 99, 'submitted_at': None, 'score': None}]

        mock_get.side_effect = [courses_resp, subs_resp]

        from django.core.management import call_command
        from io import StringIO
        call_command('sync_canvas', '--user', self.user.username, stdout=StringIO())

        self.user.refresh_from_db()
        self.assertEqual(self.user.bit_balance, 1000)  # no change
