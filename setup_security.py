"""
Deployment script for authentication and security features.

Run this after deploying the new code to set up permissions and security.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iftf_duoverkoop.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User
from iftf_duoverkoop.auth import setup_permission_groups, GROUP_POS_STAFF, GROUP_SUPPORT_STAFF


def main():
    print("=" * 70)
    print("IF Theater Festival - Security Setup")
    print("=" * 70)
    print()
    
    # Step 1: Create permission groups
    print("Step 1: Setting up permission groups...")
    try:
        setup_permission_groups()
        print(f"✓ Created/updated '{GROUP_POS_STAFF}' group")
        print(f"✓ Created/updated '{GROUP_SUPPORT_STAFF}' group")
    except Exception as e:
        print(f"✗ Error setting up groups: {e}")
        return False
    
    print()
    
    # Step 2: Check for users without groups
    print("Step 2: Checking user assignments...")
    users_without_groups = User.objects.filter(groups__isnull=True, is_superuser=False)
    if users_without_groups.exists():
        print(f"⚠ Warning: {users_without_groups.count()} user(s) need group assignment:")
        for user in users_without_groups:
            print(f"  - {user.username}")
        print()
        print("To assign users to groups, run:")
        print(f'  python manage.py assign_user_group <username> "{GROUP_POS_STAFF}"')
        print(f'  python manage.py assign_user_group <username> "{GROUP_SUPPORT_STAFF}"')
    else:
        print("✓ All non-superuser accounts have group assignments")
    
    print()
    
    # Step 3: Security reminders
    print("Step 3: Security checklist:")
    print("  [ ] Migrations applied (python manage.py migrate)")
    print("  [ ] All users assigned to groups")
    print("  [ ] SECRET_KEY set in environment variables")
    print("  [ ] DEBUG=False in production")
    print("  [ ] HTTPS enabled")
    print("  [ ] Static files collected (python manage.py collectstatic)")
    print()
    
    print("=" * 70)
    print("Setup complete! Review SECURITY_README.md for full documentation.")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

