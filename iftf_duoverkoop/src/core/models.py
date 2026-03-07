"""
core/models.py – All database models for iftf_duoverkoop.
"""
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils.translation import gettext as _
from django.utils.formats import date_format


class Association(models.Model):
    name = models.CharField(max_length=100, unique=True, primary_key=True)
    image = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class Performance(models.Model):
    key = models.CharField("Key", max_length=128, unique=True, primary_key=True)
    date = models.DateTimeField("Date")
    association = models.ForeignKey(Association, on_delete=models.CASCADE)
    name = models.CharField("Name", max_length=128)
    price = models.FloatField("Price")
    max_tickets = models.IntegerField("Maximum Tickets")

    def tickets_sold(self) -> int:
        return (
            Purchase.objects.filter(ticket1__key=self.key).count()
            + Purchase.objects.filter(ticket2__key=self.key).count()
        )

    def tickets_left(self) -> int:
        return self.max_tickets - self.tickets_sold()

    def __str__(self) -> str:
        return self.key

    def selection(self) -> str:
        return _('performance.tostring') % {
            'date': date_format(self.date, 'd b'),
            'association': self.association,
            'name': self.name,
        }


class Purchase(models.Model):
    """
    Represents a ticket purchase transaction.

    Tracks who made the purchase and maintains an audit trail
    of all modifications through the PurchaseAuditLog model.
    Each purchase has a unique three-word verification code for traceability.
    """
    date = models.DateTimeField("Date", auto_now_add=True)
    name = models.CharField("Name", max_length=128)
    email = models.EmailField("Email")
    ticket1 = models.ForeignKey(Performance, on_delete=models.PROTECT, related_name="ticket1")
    ticket2 = models.ForeignKey(Performance, on_delete=models.PROTECT, related_name="ticket2")
    verification_code = models.CharField(
        "Verification Code",
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique three-word code for purchase verification (e.g., 'happy-tree-button')",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchases_created',
        help_text="User who created this purchase",
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchases_modified',
        null=True,
        blank=True,
        help_text="User who last modified this purchase",
    )
    modified_date = models.DateTimeField("Last Modified", null=True, blank=True)

    def __str__(self) -> str:
        return f"Purchase {self.id} by {self.name} ({self.verification_code})"

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['verification_code']),
            models.Index(fields=['-date']),
        ]
        permissions = [
            ('export_data', 'Can export purchase data to CSV'),
            ('verify_purchase', 'Can look up purchases by verification code'),
        ]


class AssociationRepProfile(models.Model):
    """
    Links an Association Representative user to the association they represent.

    Each rep can be linked to exactly one association.  This is used on the
    verification page to let reps filter by one of their own performances.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='association_rep_profile',
        help_text="The association representative user account",
    )
    association = models.ForeignKey(
        Association,
        on_delete=models.CASCADE,
        related_name='rep_profiles',
        help_text="The association this representative belongs to",
    )

    def __str__(self) -> str:
        return f"{self.user.username} → {self.association.name}"

    class Meta:
        verbose_name = "Association Rep Profile"
        verbose_name_plural = "Association Rep Profiles"


class PurchaseAuditLog(models.Model):
    """
    Append-only audit log for all purchase operations.

    Tracks creation, modification, and deletion of purchases
    for security and compliance purposes.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
    ]

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text="The purchase this log entry refers to",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, help_text="Type of action performed")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="When the action occurred")
    user = models.ForeignKey(User, on_delete=models.PROTECT, help_text="User who performed the action")
    changes = models.JSONField(
        null=True, blank=True,
        help_text="JSON object containing the changes made (for UPDATE actions)",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP address of the user")

    def __str__(self) -> str:
        return f"{self.action} on Purchase {self.purchase_id} by {self.user.username} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['purchase', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]


class LoginAuditLog(models.Model):
    """Records every login, logout, and failed login attempt for security monitoring."""
    EVENT_LOGIN = 'LOGIN'
    EVENT_LOGOUT = 'LOGOUT'
    EVENT_FAILED = 'FAILED'
    EVENT_CHOICES = [
        (EVENT_LOGIN, 'Logged in'),
        (EVENT_LOGOUT, 'Logged out'),
        (EVENT_FAILED, 'Failed login attempt'),
    ]

    event = models.CharField(max_length=10, choices=EVENT_CHOICES)
    username = models.CharField(max_length=150)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='login_logs',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.event} by {self.username} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]


# ---------------------------------------------------------------------------
# Signal receivers – automatically record login / logout / failed events
# ---------------------------------------------------------------------------

def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    LoginAuditLog.objects.create(
        event=LoginAuditLog.EVENT_LOGIN,
        username=user.username,
        user=user,
        ip_address=_get_ip(request),
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user:
        LoginAuditLog.objects.create(
            event=LoginAuditLog.EVENT_LOGOUT,
            username=user.username,
            user=user,
            ip_address=_get_ip(request),
        )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    LoginAuditLog.objects.create(
        event=LoginAuditLog.EVENT_FAILED,
        username=credentials.get('username', ''),
        user=None,
        ip_address=_get_ip(request),
    )

