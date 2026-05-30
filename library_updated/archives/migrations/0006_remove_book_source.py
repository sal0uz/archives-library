# Generated migration to remove source field from Book model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archives', '0005_remove_book_source_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='book',
            name='source',
        ),
    ]
