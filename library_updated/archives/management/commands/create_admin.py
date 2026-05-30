"""
Management command: python manage.py create_admin
Creates the default admin superuser for Archives Library.
"""
from django.core.management.base import BaseCommand
from archives.models import User


class Command(BaseCommand):
    help = 'Create the default admin superuser (username: admin, password: admin123)'

    def handle(self, *args, **options):
        if User.objects.filter(username='admin').exists():
            self.stdout.write(self.style.WARNING('Admin user already exists.'))
            return

        user = User.objects.create_superuser(
            username='admin',
            email='admin@archives.library',
            password='admin123',
            first_name='Admin',
            last_name='User',
        )
        user.status = 'active'
        user.save()
        self.stdout.write(self.style.SUCCESS(
            '✅ Admin created — username: admin  |  password: admin123'
        ))
