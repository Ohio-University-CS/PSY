
# ── Space Crate ───────────────────

from django.db import migrations


SPACE_ITEMS = [
    # (name, rarity, crate_weight, sprite_path)
    ('Mercury',   'COMMON',    100, 'sprites/Items/SpaceCollection/Mercury.png'),
    ('Star',      'COMMON',    100, 'sprites/Items/SpaceCollection/Star.png'),
    ('Comet',     'COMMON',    100, 'sprites/Items/SpaceCollection/Comet.png'), 
    ('Mars',      'RARE',       40, 'sprites/Items/SpaceCollection/Mars.png'),
    ('Jupiter',   'RARE',       40, 'sprites/Items/SpaceCollection/Jupiter.png'),
    ('Earth',     'RARE',       40, 'sprites/Items/SpaceCollection/Earth.png'),
    ('Saturn',    'EPIC',       15, 'sprites/Items/SpaceCollection/Saturn.png'),
    ('Neptune',   'EPIC',       15, 'sprites/Items/SpaceCollection/Neptune.png'),
    ('Gargantua', 'LEGENDARY',   5, 'sprites/Items/SpaceCollection/Gargantua.png'),
    ('Dyson Sphere', 'LEGENDARY', 5, 'sprites/Items/SpaceCollection/DysonSphere.png'),
    ('Qu',        'SECRET',      1, 'sprites/Items/SpaceCollection/Qu.png'),
]


def create_space_crate(apps, schema_editor):
    Item         = apps.get_model('canbet_app', 'Item')
    Lootbox      = apps.get_model('canbet_app', 'Lootbox')
    LootboxEntry = apps.get_model('canbet_app', 'LootboxEntry')

    # 1. Create all Space items
    items = []
    for name, rarity, weight, sprite_path in SPACE_ITEMS:
        item, created = Item.objects.get_or_create(
            name=name,
            collection='SPACE',
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

    # 2. Create the Space LootBox
    loot_box, _ = Lootbox.objects.get_or_create(
        name='Space Crate',
        defaults={
            'crate_type': 'SPACE',
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


def delete_space_crate(apps, schema_editor):
    """Reverse migration — removes all Space crate data."""
    Item         = apps.get_model('canbet_app', 'Item')
    Lootbox      = apps.get_model('canbet_app', 'Lootbox')
    LootboxEntry = apps.get_model('canbet_app', 'LootboxEntry')

    loot_box = Lootbox.objects.filter(name='Space Crate').first()
    if loot_box:
        LootboxEntry.objects.filter(loot_box=loot_box).delete()
        loot_box.delete()

    Item.objects.filter(
        name__in=[name for name, _, _, _ in SPACE_ITEMS],
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