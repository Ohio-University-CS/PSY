from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# ── Custom User ────────────────────────────────────────────────────────────────
class CanBetUser(AbstractUser):
    """
    Extends Django's built-in User with canBet-specific fields.
    Canvas login uses the school email as the username.
    """
    bit_balance    = models.IntegerField(default=1000)
    crates_opened  = models.IntegerField(default=0)
    canvas_user_id = models.CharField(max_length=64, blank=True, null=True, unique=True)

    # profile picture stored in media/avatars/
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    class Meta:
        ordering = ['-bit_balance']

    def __str__(self):
        return self.username

    @property
    def rank(self):
        """Live leaderboard rank by bit_balance."""
        return (
            CanBetUser.objects
            .filter(bit_balance__gt=self.bit_balance)
            .count() + 1
        )


# ── Item catalogue (static definitions) ───────────────────────────────────────
class Item(models.Model):
    RARITY_CHOICES = [
        ('COMMON',    'Common'),
        ('RARE',      'Rare'),
        ('EPIC',      'Epic'),
        ('LEGENDARY', 'Legendary'),
        ('SECRET', 'Secret'),
    ]

    COLLECTION_CHOICES = [
        ('SPOOKY',  'Spooky'),
        ('SPACE',   'Space'),
        ('FANTASY', 'Fantasy'),
        ('WEATHER', 'Weather'),
    ]

    name        = models.CharField(max_length=128, unique=True)
    rarity      = models.CharField(max_length=16, choices=RARITY_CHOICES, default='COMMON')
    collection  = models.CharField(max_length=16, choices=COLLECTION_CHOICES, default='SPOOKY')
    sprite_path = models.CharField(max_length=256, blank=True)   # relative path in /static/
    shop_price  = models.IntegerField(default=0)                  # 0 = not for sale directly
    crate_weight = models.IntegerField(default=10)                # loot table weight

    class Meta:
        ordering = ['collection', 'rarity', 'name']

    def __str__(self):
        return f"{self.name} ({self.rarity})"


# ── Inventory (many-to-many with quantity) ─────────────────────────────────────
class InventoryEntry(models.Model):
    user     = models.ForeignKey(CanBetUser, on_delete=models.CASCADE, related_name='inventory')
    item     = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    obtained_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'item')

    def __str__(self):
        return f"{self.user.username} → {self.item.name} x{self.quantity}"
    

# ── Lootbox definitions ───────────────────────────────────────────────────────
class Lootbox(models.Model):
    CRATE_CHOICES = [
        ('SPOOKY',  'Spooky Crate'),
        ('SPACE',   'Space Crate'),
        ('FANTASY', 'Fantasy Crate'),
        ('WEATHER', 'Weather Crate'),
    ]

    name        = models.CharField(max_length=128, unique=True)
    crate_type  = models.CharField(max_length=16, choices=CRATE_CHOICES)
    cost_bits   = models.IntegerField(default=100)
    sprite_path = models.CharField(max_length=256, blank=True)
    is_active   = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# ── Per-item drop probabilities inside a Lootbox ──────────────────────────────
class LootboxEntry(models.Model):
    loot_box   = models.ForeignKey(Lootbox, on_delete=models.CASCADE, related_name='entries')
    item       = models.ForeignKey(Item, on_delete=models.CASCADE)
    weight     = models.PositiveIntegerField(default=10)  # relative weight, not a %

    class Meta:
        unique_together = ('loot_box', 'item')

    @property
    def drop_chance(self):
        """Returns this entry's probability as a float between 0 and 1."""
        total = self.loot_box.entries.aggregate(
            total=models.Sum('weight')
        )['total'] or 1
        return self.weight / total

    def __str__(self):
        return f"{self.loot_box.name} → {self.item.name} ({self.weight}w)"


# ── Lootboxes in a user's inventory ──────────────────────────────────────────
class LootboxInventoryEntry(models.Model):
    user      = models.ForeignKey(CanBetUser, on_delete=models.CASCADE, related_name='loot_box_inventory')
    loot_box  = models.ForeignKey(Lootbox, on_delete=models.CASCADE)
    quantity  = models.PositiveIntegerField(default=1)
    obtained_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'loot_box')

    def __str__(self):
        return f"{self.user.username} → {self.loot_box.name} x{self.quantity}"


# ── Crate opens (activity log) ─────────────────────────────────────────────────
class CrateOpen(models.Model):
    CRATE_CHOICES = [
        ('SPOOKY',  'Spooky Crate'),
        ('SPACE',   'Space Crate'),
        ('FANTASY', 'Fantasy Crate'),
        ('WEATHER', 'Weather Crate'),
    ]

    user       = models.ForeignKey(CanBetUser, on_delete=models.CASCADE, related_name='crate_opens')
    crate_type = models.CharField(max_length=16, choices=CRATE_CHOICES)
    item_won   = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    bits_spent = models.IntegerField(default=0)
    opened_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.user.username} opened {self.crate_type} → {self.item_won}"


# ── Shop purchase log ──────────────────────────────────────────────────────────
class ShopPurchase(models.Model):
    user       = models.ForeignKey(CanBetUser, on_delete=models.CASCADE, related_name='purchases')
    item       = models.ForeignKey(Item, on_delete=models.CASCADE)
    bits_spent = models.IntegerField()
    purchased_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-purchased_at']

    def __str__(self):
        return f"{self.user.username} bought {self.item.name} for {self.bits_spent} bits"


# ── Canvas grade snapshot (populated by management command) ───────────────────
class CanvasSubmission(models.Model):
    user           = models.ForeignKey(CanBetUser, on_delete=models.CASCADE, related_name='canvas_submissions')
    course_name    = models.CharField(max_length=256)
    course_id      = models.CharField(max_length=64)
    assignment_id  = models.CharField(max_length=64, blank=True)
    submitted_at   = models.DateTimeField(null=True, blank=True)
    score          = models.FloatField(null=True, blank=True)
    fetched_at     = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ('user', 'course_id', 'assignment_id')

    def __str__(self):
        return f"{self.user.username} — {self.course_name}"

