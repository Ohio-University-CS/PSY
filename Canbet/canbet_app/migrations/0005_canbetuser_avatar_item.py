from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('canbet_app', '0004_spooky_collection'),
    ]

    operations = [
        migrations.AddField(
            model_name='canbetuser',
            name='avatar_item',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='avatar_users',
                to='canbet_app.item',
            ),
        ),
    ]
