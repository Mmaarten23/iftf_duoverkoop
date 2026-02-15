"""
Management command to initialize permission groups and security settings.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from iftf_duoverkoop.auth import setup_permission_groups, GROUP_POS_STAFF, GROUP_SUPPORT_STAFF


class Command(BaseCommand):
    help = 'Initialize permission groups for POS Staff and Support Staff'

    def handle(self, *args, **options):
        self.stdout.write('Setting up permission groups...')

        try:
            setup_permission_groups()
            self.stdout.write(self.style.SUCCESS(f'✓ Successfully created/updated permission groups'))
            self.stdout.write(f'  - {GROUP_POS_STAFF}: Can create purchases and view history')
            self.stdout.write(f'  - {GROUP_SUPPORT_STAFF}: Can create, edit, delete purchases and export data')

            # Show existing users without groups
            users_without_groups = User.objects.filter(groups__isnull=True, is_superuser=False)
            if users_without_groups.exists():
                self.stdout.write(self.style.WARNING(
                    f'\nWarning: {users_without_groups.count()} user(s) without group assignment:'
                ))
                for user in users_without_groups:
                    self.stdout.write(f'  - {user.username}')
                self.stdout.write('\nTo assign users to groups, use:')
                self.stdout.write('  python manage.py assign_user_group <username> <group_name>')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error setting up permission groups: {str(e)}'))
            raise

