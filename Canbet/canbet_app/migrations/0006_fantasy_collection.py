
# ── Fantasy Crate ───────────────────

from django.db import migrations


FANTASY_ITEMS = [
    # (name, rarity, crate_weight, sprite_path)
    # ('Mercury',   'COMMON',    100, 'sprites/Items/FantasyCollection/Mercury.png'),
    # ('Star',      'COMMON',    100, 'sprites/Items/FantasyCollection/Star.png'),
    # ('Mars',      'RARE',       40, 'sprites/Items/FantasyCollection/Mars.png'),
    ('Wizard Tower',   'RARE',       40, 'sprites/Items/FantasyCollection/Jupiter.png'),
    ('Fairy',     'RARE',       40, 'sprites/Items/FantasyCollection/Earth.png'),
    ('Chosen Knight',    'EPIC',       15, 'sprites/Items/FantasyCollection/Saturn.png'),
    ('Dom, the Wizard of Destiny',   'EPIC',       15, 'sprites/Items/FantasyCollection/Neptune.png'),
    ('Dragon', 'LEGENDARY',   5, 'sprites/Items/FantasyCollection/Gargantua.png'),
    ('Adventuring party', 'LEGENDARY', 5, 'sprites/Items/FantasyCollection/DysonSphere.png'),
    # ('Qu',         'SECRET',     1, 'sprites/Items/FantasyCollection/Qu.png'),
]


def create_fantasy_crate(apps, schema_editor):
    Item         = apps.get_model('canbet_app', 'Item')
    Lootbox      = apps.get_model('canbet_app', 'Lootbox')
    LootboxEntry = apps.get_model('canbet_app', 'LootboxEntry')

    # 1. Create all Fantasy items
    items = []
    for name, rarity, weight, sprite_path in FANTASY_ITEMS:
        item, created = Item.objects.get_or_create(
            name=name,
            collection='FANTASY',
            defaults={
                'rarity':       rarity,
                'shop_price':   0,
                'crate_weight': weight,
                'sprite_path':  sprite_path,
            }
        )
        # Update sprite_path even if item already exists
        if item.sprite_path != sprite_path:
            item.sprite_path = sprite_path
            item.save()
        items.append((item, weight))

    # 2. Create the Fantasy Lootbox
    loot_box, _ = Lootbox.objects.get_or_create(
        name='Fantasy Crate',
        defaults={
            'crate_type': 'FANTASY',
            'cost_bits':  200,
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


def delete_fantasy_crate(apps, schema_editor):
    """Reverse migration — removes all Fantasy crate data."""
    Item         = apps.get_model('canbet_app', 'Item')
    Lootbox      = apps.get_model('canbet_app', 'Lootbox')
    LootboxEntry = apps.get_model('canbet_app', 'LootboxEntry')

    loot_box = Lootbox.objects.filter(name='Fantasy Crate').first()
    if loot_box:
        LootboxEntry.objects.filter(loot_box=loot_box).delete()
        loot_box.delete()

    Item.objects.filter(
        name__in=[name for name, _, _, _ in FANTASY_ITEMS],
        collection='FANTASY'
    ).delete()


class Migration(migrations.Migration):

    # !! Replace '0001_initial' with the name of your actual last migration !!
    dependencies = [
        ('canbet_app', '0005_canbetuser_avatar_item'),
    ]

    operations = [
        migrations.RunPython(create_fantasy_crate, delete_fantasy_crate),
    ]