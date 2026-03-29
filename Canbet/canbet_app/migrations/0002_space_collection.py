
# ── Space Crate ───────────────────

from django.db import migrations


SPACE_ITEMS = [
    # (name, rarity, crate_weight)
    ('Mercury',   'COMMON',    100),
    ('Star',      'COMMON',    100),
    ('Mars',      'RARE',       40),
    ('Jupiter',   'RARE',       40),
    ('Earth',     'RARE',       40),
    ('Saturn',    'EPIC',       15),
    ('Neptune',   'EPIC',       15),
    ('Gargantua', 'LEGENDARY',   5),
    ('Dyson Sphere', 'LEGENDARY', 5),
]


def create_space_crate(apps, schema_editor):
    Item        = apps.get_model('canbet_app', 'Item')
    Lootbox     = apps.get_model('canbet_app', 'Lootbox')
    LootboxEntry = apps.get_model('canbet_app', 'LootboxEntry')

    # 1. Create all Space items
    items = []
    for name, rarity, weight in SPACE_ITEMS:
        item, _ = Item.objects.get_or_create(
            name=name,
            defaults={
                'rarity':       rarity,
                'collection':   'SPACE',
                'shop_price':   0,
                'crate_weight': weight,
            }
        )
        items.append((item, weight))

    # 2. Create the Space LootBox
    loot_box, _ = Lootbox.objects.get_or_create(
        name='Space Crate',
        defaults={
            'crate_type': 'SPACE',
            'cost_bits':  100,
            'is_active':  True,
        }
    )

    # 3. Link each item to the crate with its drop weight
    for item, weight in items:
        LootboxEntry.objects.get_or_create(
            loot_box=loot_box,
            item=item,
            defaults={'weight': weight}
        )


def delete_space_crate(apps, schema_editor):
    """Reverse migration — removes all Space crate data."""
    Item         = apps.get_model('canbet_app', 'Item')
    LootBox      = apps.get_model('canbet_app', 'LootBox')
    LootBoxEntry = apps.get_model('canbet_app', 'LootBoxEntry')

    loot_box = LootBox.objects.filter(name='Space Crate').first()
    if loot_box:
        LootBoxEntry.objects.filter(loot_box=loot_box).delete()
        loot_box.delete()

    Item.objects.filter(
        name__in=[name for name, _, _ in SPACE_ITEMS],
        collection='SPACE'
    ).delete()


class Migration(migrations.Migration):

    # !! Replace '0001_initial' with the name of your actual last migration !!
    dependencies = [
        ('canbet_app', '0003_lootbox_lootboxentry_lootboxinventoryentry'),
    ]

    operations = [
        migrations.RunPython(create_space_crate, delete_space_crate),
    ]