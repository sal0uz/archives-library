# Generated migration to remove source_url field from Book model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archives', '0004_postcomment_likes'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='book',
            name='source_url',
        ),
    ]
