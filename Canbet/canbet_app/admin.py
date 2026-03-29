from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CanBetUser, Item, InventoryEntry, CrateOpen, ShopPurchase, CanvasSubmission, Lootbox, LootboxEntry, LootboxInventoryEntry


@admin.register(CanBetUser)
class CanBetUserAdmin(UserAdmin):
    list_display  = ('username', 'email', 'bit_balance', 'crates_opened', 'canvas_user_id')
    list_filter   = ('is_staff', 'is_active')
    search_fields = ('username', 'email', 'canvas_user_id')
    fieldsets     = UserAdmin.fieldsets + (
        ('canBet', {'fields': ('bit_balance', 'crates_opened', 'canvas_user_id', 'avatar')}),
    )


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display  = ('name', 'rarity', 'collection', 'shop_price', 'crate_weight')
    list_filter   = ('rarity', 'collection')
    search_fields = ('name',)


@admin.register(InventoryEntry)
class InventoryEntryAdmin(admin.ModelAdmin):
    list_display  = ('user', 'item', 'quantity', 'obtained_at')
    list_filter   = ('item__rarity', 'item__collection')
    search_fields = ('user__username', 'item__name')


@admin.register(CrateOpen)
class CrateOpenAdmin(admin.ModelAdmin):
    list_display  = ('user', 'crate_type', 'item_won', 'bits_spent', 'opened_at')
    list_filter   = ('crate_type', 'item_won__rarity')
    search_fields = ('user__username',)


@admin.register(ShopPurchase)
class ShopPurchaseAdmin(admin.ModelAdmin):
    list_display  = ('user', 'item', 'bits_spent', 'purchased_at')
    search_fields = ('user__username', 'item__name')


@admin.register(CanvasSubmission)
class CanvasSubmissionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'course_name', 'assignment_id', 'submitted_at', 'score')
    list_filter   = ('course_name',)
    search_fields = ('user__username', 'course_name')


@admin.register(Lootbox)
class LootboxAdmin(admin.ModelAdmin):
    list_display  = ('name', 'crate_type', 'cost_bits', 'is_active')
    list_filter   = ('crate_type', 'is_active')
    search_fields = ('name',)


@admin.register(LootboxEntry)
class LootboxEntryAdmin(admin.ModelAdmin):
    list_display  = ('loot_box', 'item', 'weight', 'drop_chance')
    list_filter   = ('loot_box', 'item__rarity')
    search_fields = ('loot_box__name', 'item__name')


@admin.register(LootboxInventoryEntry)
class LootboxInventoryEntryAdmin(admin.ModelAdmin):
    list_display  = ('user', 'loot_box', 'quantity', 'obtained_at')
    list_filter   = ('loot_box',)
    search_fields = ('user__username', 'loot_box__name')