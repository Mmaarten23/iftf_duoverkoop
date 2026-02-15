"""
Authentication and authorization utilities.

Defines permission groups and helper functions for role-based access control.
"""
from typing import Optional
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from iftf_duoverkoop.models import Purchase, PurchaseAuditLog


# Permission group names
GROUP_POS_STAFF = 'POS Staff'
GROUP_SUPPORT_STAFF = 'Support Staff'


def setup_permission_groups() -> None:
    """
    Create and configure permission groups for the application.

    - POS Staff: Can create purchases and view history (read-only)
    - Support Staff: Can do everything POS Staff can do, plus edit/delete purchases and export data
    """
    purchase_ct = ContentType.objects.get_for_model(Purchase)

    with transaction.atomic():
        # Create POS Staff group
        pos_group, _ = Group.objects.get_or_create(name=GROUP_POS_STAFF)
        pos_permissions = [
            Permission.objects.get(codename='add_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='view_purchase', content_type=purchase_ct),
        ]
        pos_group.permissions.set(pos_permissions)

        # Create Support Staff group
        support_group, _ = Group.objects.get_or_create(name=GROUP_SUPPORT_STAFF)
        support_permissions = [
            Permission.objects.get(codename='add_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='view_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='change_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='delete_purchase', content_type=purchase_ct),
        ]
        support_group.permissions.set(support_permissions)


def is_pos_staff(user: User) -> bool:
    """Check if user is a member of POS Staff group."""
    return user.groups.filter(name=GROUP_POS_STAFF).exists()


def is_support_staff(user: User) -> bool:
    """Check if user is a member of Support Staff group."""
    return user.groups.filter(name=GROUP_SUPPORT_STAFF).exists()


def can_edit_purchases(user: User) -> bool:
    """Check if user has permission to edit purchases (Support Staff only)."""
    return user.has_perm('iftf_duoverkoop.change_purchase')


def can_export_data(user: User) -> bool:
    """Check if user has permission to export data (Support Staff only)."""
    return is_support_staff(user)


def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP address from request.

    Handles both direct connections and proxied requests (X-Forwarded-For).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_purchase_action(
    purchase: Purchase,
    action: str,
    user: User,
    ip_address: Optional[str] = None,
    changes: Optional[dict] = None
) -> PurchaseAuditLog:
    """
    Create an audit log entry for a purchase action.

    Args:
        purchase: The purchase being acted upon
        action: Type of action ('CREATE', 'UPDATE', or 'DELETE')
        user: User performing the action
        ip_address: IP address of the user (optional)
        changes: Dictionary of changes made (for UPDATE actions)

    Returns:
        The created PurchaseAuditLog instance
    """
    log_entry = PurchaseAuditLog.objects.create(
        purchase=purchase,
        action=action,
        user=user,
        ip_address=ip_address,
        changes=changes
    )
    return log_entry

