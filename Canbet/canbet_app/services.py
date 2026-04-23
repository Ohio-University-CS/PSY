import random
from django.db import transaction, models
from .models import CanBetUser, LootboxInventoryEntry, LootboxEntry, InventoryEntry, CrateOpen, Lootbox

def open_loot_box(user, loot_box):
    with transaction.atomic():
        entry = LootboxInventoryEntry.objects.select_for_update().get(
            user=user, loot_box=loot_box, quantity__gte=1
        )
        entry.quantity -= 1
        if entry.quantity == 0:
            entry.delete()
        else:
            entry.save()

        pool = list(LootboxEntry.objects.filter(loot_box=loot_box).select_related('item'))
        if not pool:
            raise ValueError(f"{loot_box.name} has no items configured.")

        weights = [e.weight for e in pool]
        won_entry = random.choices(pool, weights=weights, k=1)[0]
        won_item = won_entry.item

        inv, _ = InventoryEntry.objects.get_or_create(user=user, item=won_item, defaults={'quantity': 0})       
        inv.quantity += 1
        inv.save()

        CrateOpen.objects.create(
            user=user,
            crate_type=loot_box.crate_type,
            item_won=won_item,
            bits_spent=loot_box.cost_bits,
        )

        CanBetUser.objects.filter(pk=user.pk).update(
            crates_opened=models.F('crates_opened') + 1
        )
        user.crates_opened += 1  # keep in-memory object consistent

        return won_item


def award_loot_box(user, loot_box_name, quantity=1):
    loot_box = Lootbox.objects.get(name=loot_box_name)
    entry, _ = LootboxInventoryEntry.objects.get_or_create(
        user=user, loot_box=loot_box,
        defaults={'quantity': 0}
    )
    entry.quantity += quantity
    entry.save()