"""
Management command to assign users to permission groups.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from iftf_duoverkoop.auth import GROUP_POS_STAFF, GROUP_SUPPORT_STAFF


class Command(BaseCommand):
    help = 'Assign a user to a permission group (POS Staff or Support Staff)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to assign to group')
        parser.add_argument(
            'group',
            type=str,
            choices=[GROUP_POS_STAFF, GROUP_SUPPORT_STAFF],
            help=f'Group name: "{GROUP_POS_STAFF}" or "{GROUP_SUPPORT_STAFF}"'
        )

    def handle(self, *args, **options):
        username = options['username']
        group_name = options['group']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')

        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            raise CommandError(
                f'Group "{group_name}" does not exist. Run "python manage.py setup_permissions" first.'
            )

        # Remove user from other groups (to ensure they're only in one role group)
        user.groups.clear()
        user.groups.add(group)

        self.stdout.write(self.style.SUCCESS(
            f'✓ Successfully assigned user "{username}" to group "{group_name}"'
        ))

        # Show user's permissions
        if group_name == GROUP_POS_STAFF:
            self.stdout.write('  Permissions: Create purchases, View purchase history (read-only)')
        else:
            self.stdout.write('  Permissions: Create/Edit/Delete purchases, Export data, View history')

