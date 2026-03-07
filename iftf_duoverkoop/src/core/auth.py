"""
core/auth.py – Permission groups, role helpers, audit log helper.
"""
from typing import Optional, TYPE_CHECKING
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

if TYPE_CHECKING:
    from iftf_duoverkoop.src.core.models import Purchase, PurchaseAuditLog


# Permission group names
GROUP_POS_STAFF = 'POS Staff'
GROUP_SUPPORT_STAFF = 'Support Staff'
GROUP_ASSOCIATION_REP = 'Association Representative'


def setup_permission_groups() -> None:
    """
    Create and configure permission groups for the application.

    - POS Staff: Can create purchases and view purchase history (read-only).
    - Support Staff: Everything POS Staff can do, plus edit/delete purchases,
      export data, and verify purchases by code.
    - Association Representative: Can only look up purchases by verification code.
    """
    from iftf_duoverkoop.src.core.models import Purchase  # local import avoids circularity
    purchase_ct = ContentType.objects.get_for_model(Purchase)

    with transaction.atomic():
        pos_group, _ = Group.objects.get_or_create(name=GROUP_POS_STAFF)
        pos_group.permissions.set([
            Permission.objects.get(codename='add_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='view_purchase', content_type=purchase_ct),
        ])

        support_group, _ = Group.objects.get_or_create(name=GROUP_SUPPORT_STAFF)
        support_group.permissions.set([
            Permission.objects.get(codename='add_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='view_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='change_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='delete_purchase', content_type=purchase_ct),
            Permission.objects.get(codename='export_data', content_type=purchase_ct),
            Permission.objects.get(codename='verify_purchase', content_type=purchase_ct),
        ])

        rep_group, _ = Group.objects.get_or_create(name=GROUP_ASSOCIATION_REP)
        rep_group.permissions.set([
            Permission.objects.get(codename='verify_purchase', content_type=purchase_ct),
        ])


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def is_pos_staff(user: User) -> bool:
    return user.groups.filter(name=GROUP_POS_STAFF).exists()


def is_support_staff(user: User) -> bool:
    return user.groups.filter(name=GROUP_SUPPORT_STAFF).exists()


def is_association_rep(user: User) -> bool:
    return user.groups.filter(name=GROUP_ASSOCIATION_REP).exists()


def can_edit_purchases(user: User) -> bool:
    return user.has_perm('iftf_duoverkoop.change_purchase')


def can_export_data(user: User) -> bool:
    return user.has_perm('iftf_duoverkoop.export_data')


def can_verify_tickets(user: User) -> bool:
    return user.has_perm('iftf_duoverkoop.verify_purchase')


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------

def get_client_ip(request) -> Optional[str]:
    """Extract client IP, honouring X-Forwarded-For for proxied deployments."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


def _purchase_snapshot(purchase: 'Purchase') -> dict:
    """
    Return a flat dict capturing the full observable state of a Purchase.
    Used as the canonical snapshot format inside audit log ``changes`` payloads.
    """
    return {
        'id': purchase.pk,
        'name': purchase.name,
        'email': purchase.email,
        'ticket1': purchase.ticket1.key,
        'ticket2': purchase.ticket2.key,
        'verification_code': purchase.verification_code,
        'created_by': purchase.created_by.username,
        'created_at': purchase.date.isoformat(),
        'modified_by': purchase.modified_by.username if purchase.modified_by else None,
        'modified_at': purchase.modified_date.isoformat() if purchase.modified_date else None,
    }


def log_purchase_action(
    purchase: 'Purchase',
    action: str,
    user: User,
    ip_address: Optional[str] = None,
    changes: Optional[dict] = None,
) -> 'PurchaseAuditLog':
    """
    Create an append-only audit log entry for a purchase action.

    The ``changes`` argument carries a structured, self-contained payload:

    CREATE
        Pass ``changes=None``; the full purchase state is captured automatically
        as ``{'state': <snapshot>}``.

    UPDATE
        Pass a dict with keys ``'before'`` and ``'after'`` (each a snapshot dict)
        plus ``'diff'`` (only the changed fields).  If only a partial ``'diff'``
        dict is supplied the helper wraps it for backwards compatibility.

    DELETE
        Pass ``changes=None``; the full final state is captured automatically
        as ``{'final_state': <snapshot>}``.

    Any caller may also pass a fully-formed ``changes`` dict to override this
    behaviour (used by the order-creation view which pre-builds the payload).
    """
    from iftf_duoverkoop.src.core.models import PurchaseAuditLog  # local import avoids circularity

    if action == 'CREATE' and changes is None:
        changes = {'state': _purchase_snapshot(purchase)}

    elif action == 'DELETE' and changes is None:
        changes = {'final_state': _purchase_snapshot(purchase)}

    return PurchaseAuditLog.objects.create(
        purchase=purchase,
        purchase_id_snapshot=purchase.pk,
        action=action,
        user=user,
        ip_address=ip_address,
        changes=changes,
    )
