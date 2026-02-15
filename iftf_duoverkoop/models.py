from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext as _


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
        return Purchase.objects.filter(ticket1__key=self.key).count() + Purchase.objects.filter(
            ticket2__key=self.key).count()

    def tickets_left(self) -> int:
        return self.max_tickets - self.tickets_sold()

    def __str__(self) -> str:
        return self.key

    def selection(self) -> str:
        return _('performance.tostring') % {
            'date': self.date.strftime("%d %b"),
            'association': self.association,
            'name': self.name
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
        help_text="Unique three-word code for purchase verification (e.g., 'happy-tree-button')"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchases_created',
        help_text="User who created this purchase"
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchases_modified',
        null=True,
        blank=True,
        help_text="User who last modified this purchase"
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
        help_text="The purchase this log entry refers to"
    )
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    timestamp = models.DateTimeField(auto_now_add=True, help_text="When the action occurred")
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        help_text="User who performed the action"
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON object containing the changes made (for UPDATE actions)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user who made the change"
    )

    def __str__(self) -> str:
        return f"{self.action} on Purchase {self.purchase_id} by {self.user.username} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['purchase', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]

