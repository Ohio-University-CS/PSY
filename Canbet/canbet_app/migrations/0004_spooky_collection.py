# ── Spooky Crate ───────────────────

from django.db import migrations


SPOOKY_ITEMS = [
    # (name, rarity, crate_weight)
    ('Angry Ghost',                 'COMMON',     100),
    ('Happy Ghost',                 'COMMON',     100),
    ('Zombie',                      'COMMON',     100),
    ('Mummy',                       'RARE',        50),
    ('Vampire',                     'RARE',        50),
    ('Gargoyle',                    'RARE',        50),
    ('Creature from the Black Lagoon', 'EPIC',     20),
    ('Evil Robot',                  'EPIC',        20),
    ('Flying Spaghetti Monster',    'LEGENDARY',    5),
    ('Cthulhu',                     'LEGENDARY',    5),
]


def create_spooky_crate(apps, schema_editor):
    Item         = apps.get_model('canbet_app', 'Item')
    Lootbox      = apps.get_model('canbet_app', 'Lootbox')
    LootboxEntry = apps.get_model('canbet_app', 'LootboxEntry')

    # 1. Create all Spooky items
    items = []
    for name, rarity, weight in SPOOKY_ITEMS:
        item, _ = Item.objects.get_or_create(
            name=name,
            defaults={
                'rarity':       rarity,
                'collection':   'SPOOKY',
                'shop_price':   0,
                'crate_weight': weight,
            }
        )
        items.append((item, weight))

    # 2. Create the Spooky LootBox
    loot_box, _ = Lootbox.objects.get_or_create(
        name='Spooky Crate',
        defaults={
            'crate_type': 'SPOOKY',
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


def delete_spooky_crate(apps, schema_editor):
    """Reverse migration — removes all Spooky crate data."""
    Item         = apps.get_model('canbet_app', 'Item')
    Lootbox      = apps.get_model('canbet_app', 'Lootbox')
    LootboxEntry = apps.get_model('canbet_app', 'LootboxEntry')

    loot_box = Lootbox.objects.filter(name='Spooky Crate').first()
    if loot_box:
        LootboxEntry.objects.filter(loot_box=loot_box).delete()
        loot_box.delete()

    Item.objects.filter(
        name__in=[name for name, _, _ in SPOOKY_ITEMS],
        collection='SPOOKY'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('canbet_app', '0002_space_collection'),
    ]

    operations = [
        migrations.RunPython(create_spooky_crate, delete_spooky_crate),
    ]
