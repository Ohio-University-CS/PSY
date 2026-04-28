from django.db import migrations

SPRITE_FIXES = {
    'Wizard Tower':               'sprites/Items/FantasyCollection/Wizard tower.png',
    'Fairy':                      'sprites/Items/FantasyCollection/fairy.png',
    'Chosen Knight':              'sprites/Items/FantasyCollection/Chosen Knight.png',
    'Dom, the Wizard of Destiny': 'sprites/Items/FantasyCollection/Dom The Wizard Of Destiny.png',
    'Dragon':                     'sprites/Items/FantasyCollection/Dragon.png',
    'Adventuring party':          'sprites/Items/FantasyCollection/aventuring party.png',
}


def fix_fantasy_sprites(apps, schema_editor):
    Item = apps.get_model('canbet_app', 'Item')
    for name, sprite_path in SPRITE_FIXES.items():
        Item.objects.filter(name=name, collection='FANTASY').update(sprite_path=sprite_path)


def reverse_fantasy_sprites(apps, schema_editor):
    old_paths = {
        'Wizard Tower':               'sprites/Items/FantasyCollection/Jupiter.png',
        'Fairy':                      'sprites/Items/FantasyCollection/Earth.png',
        'Chosen Knight':              'sprites/Items/FantasyCollection/Saturn.png',
        'Dom, the Wizard of Destiny': 'sprites/Items/FantasyCollection/Neptune.png',
        'Dragon':                     'sprites/Items/FantasyCollection/Gargantua.png',
        'Adventuring party':          'sprites/Items/FantasyCollection/DysonSphere.png',
    }
    Item = apps.get_model('canbet_app', 'Item')
    for name, sprite_path in old_paths.items():
        Item.objects.filter(name=name, collection='FANTASY').update(sprite_path=sprite_path)


class Migration(migrations.Migration):

    dependencies = [
        ('canbet_app', '0006_fantasy_collection'),
    ]

    operations = [
        migrations.RunPython(fix_fantasy_sprites, reverse_fantasy_sprites),
    ]
