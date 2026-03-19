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
    discounted_price = models.FloatField(
        "Discounted Price (culture card)",
        null=True,
        blank=True,
        help_text="Reduced price for buyers with a culture card (cultuurkaart). Leave blank if no discount applies.",
    )
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
    EMAIL_PENDING = 'PENDING'
    EMAIL_SENT = 'SENT'
    EMAIL_FAILED = 'FAILED'
    EMAIL_NOT_SENT = 'NOT_SENT'
    EMAIL_STATUS_CHOICES = [
        (EMAIL_PENDING, 'Pending'),
        (EMAIL_SENT, 'Sent'),
        (EMAIL_FAILED, 'Failed'),
        (EMAIL_NOT_SENT, 'Not sent (disabled)'),
    ]

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
    email_status = models.CharField(
        "Email Status",
        max_length=10,
        choices=EMAIL_STATUS_CHOICES,
        default=EMAIL_PENDING,
        db_index=True,
        help_text="Tracks whether the confirmation email was successfully delivered.",
    )
    has_culture_card = models.BooleanField(
        "Has culture card",
        default=False,
        help_text="Whether the buyer presented a culture card (cultuurkaart) for a discount.",
    )
    student_id = models.CharField(
        "Student ID",
        max_length=20,
        blank=True,
        default='',
        help_text="Student ID (e.g. r0000000) required when a culture-card discount is applied.",
    )

    def ticket1_price(self) -> float:
        """Return the price actually charged for ticket 1, respecting any culture-card discount."""
        if self.has_culture_card and self.ticket1.discounted_price is not None:
            return self.ticket1.discounted_price
        return self.ticket1.price

    def ticket2_price(self) -> float:
        """Return the price actually charged for ticket 2, respecting any culture-card discount."""
        if self.has_culture_card and self.ticket2.discounted_price is not None:
            return self.ticket2.discounted_price
        return self.ticket2.price

    def total_price(self) -> float:
        """Return the total price for this purchase."""
        return self.ticket1_price() + self.ticket2_price()

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


class EmailTemplateSettings(models.Model):
    """
    Singleton-like settings row for purchase confirmation emails.

    Managed via dashboard/system so staff can tune content and styling
    without a code deploy.
    """
    singleton_key = models.CharField(max_length=20, unique=True, default='default', editable=False)
    subject_template = models.TextField(
        default='IFTF duo ticket confirmation - {{ verification_code }}',
        help_text='Template variables: {{ name }}, {{ verification_code }}, {{ performance1 }}, {{ performance2 }}, {{ purchase_date }}, {{ total_price }}.',
    )
    text_template = models.TextField(
        default=(
            'Hi {{ name }},\n\n'
            'Your duo ticket was registered successfully.\n\n'
            'Ticket 1: {{ performance1 }}\n'
            'Ticket 2: {{ performance2 }}\n'
            'Order date: {{ purchase_date }}\n'
            'Total paid: EUR {{ total_price }}\n\n'
            'Verification code: {{ verification_code }}\n\n'
            '{{ culture_card_line }}\n'
            '1. This email only confirms your duo ticket sale. Practical details are shared by each association.\n'
            '2. Information sent by the associations is the source of truth. Associations may send separate tickets through their own systems.\n'
            '3. Keep your verification code easily accessible. It may be used at performance entrances, depending on association policy.\n'
            '4. Report disputes or incorrect recipient information to https://iftf.be/contact/.\n'
            '5. More information: https://iftf.be\n'
        ),
        help_text='Plain-text fallback body (Django template syntax).',
    )
    html_template = models.TextField(
        default=(
            '<!doctype html>'
            '<html><body style="margin:0;padding:0;background:{{ background_color }};font-family:Arial,sans-serif;">'
            '<div style="max-width:{{ content_width }}px;margin:24px auto;background:{{ card_background_color }};'
            'border:1px solid {{ border_color }};border-radius:10px;overflow:hidden;">'
            '<div style="padding:16px 20px;background:{{ primary_color }};color:#fff;display:flex;align-items:center;gap:16px;">'
            '{% if iftf_logo_url %}'
            '<img src="{{ iftf_logo_url }}" alt="IFTF" '
            'style="max-height:28px;max-width:28px;object-fit:contain;background:#fff;border-radius:4px;padding:2px;">'
            '{% endif %}'
            '<h2 style="margin:0;font-size:20px;">IFTF DuoVerkoop</h2>'
            '</div>'
            '<div style="padding:20px;color:#212529;line-height:1.5;">'
            '<p style="margin-top:0;">Hi <strong>{{ name }}</strong>, your duo ticket is confirmed.</p>'
            '<p>'
            '<strong>Ticket 1:</strong> {{ performance1 }}<br>'
            '<strong>Ticket 2:</strong> {{ performance2 }}<br>'
            '<strong>Order date:</strong> {{ purchase_date }}<br>'
            '<strong>Total paid:</strong> EUR {{ total_price }}'
            '</p>'
            '<p style="padding:12px 14px;background:#f8f9fa;border:1px solid {{ border_color }};border-radius:8px;">'
            '<strong>Verification code:</strong> '
            '<span style="color:{{ accent_color }};font-size:17px;">{{ verification_code }}</span>'
            '</p>'
            '{% if culture_card_line %}<p style="margin:0 0 10px 0;">{{ culture_card_line }}</p>{% endif %}'
            '<div style="margin-top:16px;padding-top:12px;border-top:1px solid {{ border_color }};">'
            '<p style="margin:0 0 8px 0;"><strong>Important information</strong></p>'
            '<ol style="margin:0 0 10px 20px;padding:0;">'
            '<li style="margin-bottom:6px;">This email only confirms your duo ticket sale. Practical details are shared by each association.</li>'
            '<li style="margin-bottom:6px;">Information sent by the associations is the source of truth. Associations may send separate tickets through their own systems.</li>'
            '<li style="margin-bottom:6px;">Keep your verification code easily accessible. It may be used at performance entrances, depending on association policy.</li>'
            '<li style="margin-bottom:6px;">Report disputes or incorrect recipient information to <a href="https://iftf.be/contact/">https://iftf.be/contact/</a>.</li>'
            '<li>More information: <a href="https://iftf.be">https://iftf.be</a></li>'
            '</ol>'
            '</div>'
            '<p style="margin-bottom:0;">{{ footer_text }}</p>'
            '</div></div></body></html>'
        ),
        help_text='HTML body (Django template syntax).',
    )
    primary_color = models.CharField(max_length=7, default='#0d6efd')
    accent_color = models.CharField(max_length=7, default='#198754')
    background_color = models.CharField(max_length=7, default='#f5f7fb')
    card_background_color = models.CharField(max_length=7, default='#ffffff')
    border_color = models.CharField(max_length=7, default='#dbe3ec')
    content_width = models.PositiveIntegerField(default=640)
    footer_text = models.CharField(max_length=255, default='See you at the IFTF performances.')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(singleton_key='default')
        return obj

    def __str__(self) -> str:
        return 'Email Template Settings'

    class Meta:
        verbose_name = 'Email Template Settings'
        verbose_name_plural = 'Email Template Settings'


class EmailCampaign(models.Model):
    """Represents a follow-up email campaign to a selected audience."""
    AUDIENCE_ALL = 'ALL'
    AUDIENCE_ASSOCIATIONS = 'ASSOCIATIONS'
    AUDIENCE_PERFORMANCE = 'PERFORMANCE'
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, 'All customers'),
        (AUDIENCE_ASSOCIATIONS, 'Specific associations'),
        (AUDIENCE_PERFORMANCE, 'Specific performance'),
    ]

    STATUS_QUEUED = 'QUEUED'
    STATUS_RUNNING = 'RUNNING'
    STATUS_SUCCEEDED = 'SUCCEEDED'
    STATUS_PARTIAL_FAILED = 'PARTIAL_FAILED'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_PARTIAL_FAILED, 'Partially failed'),
        (STATUS_FAILED, 'Failed'),
    ]

    name = models.CharField(max_length=150)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='email_campaigns_created')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    audience_type = models.CharField(max_length=20, choices=AUDIENCE_CHOICES)
    audience_associations = models.ManyToManyField('Association', blank=True)
    audience_performance = models.ForeignKey('Performance', null=True, blank=True, on_delete=models.SET_NULL)

    subject_template = models.TextField()
    text_template = models.TextField(blank=True, default='')
    html_template = models.TextField(blank=True, default='')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')

    def __str__(self) -> str:
        return f'Campaign {self.id}: {self.name}'

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('manage_email_campaigns', 'Can create and send email campaigns'),
            ('view_email_campaign_reports', 'Can view email campaign reports'),
        ]


class EmailCampaignRecipient(models.Model):
    """Delivery status row for one recipient inside a campaign."""
    STATUS_PENDING = 'PENDING'
    STATUS_SENT = 'SENT'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name='recipients')
    purchase = models.ForeignKey('Purchase', null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField(db_index=True)
    customer_name = models.CharField(max_length=128, blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    audience_context = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['email']
        unique_together = [('campaign', 'email')]

    def __str__(self) -> str:
        return f'{self.campaign_id} -> {self.email} ({self.status})'


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

    The FK to Purchase uses SET_NULL so that log entries are never deleted
    when a purchase is deleted.  The purchase's numeric ID is also stored in
    ``purchase_id_snapshot`` so it is readable even after the Purchase row
    itself is gone.  The full before/after state is always stored in
    ``changes`` so the log is self-contained.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
    ]

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="The purchase this log entry refers to (NULL once the purchase is deleted)",
    )
    purchase_id_snapshot = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Numeric purchase ID captured at log time; survives purchase deletion",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, help_text="Type of action performed")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="When the action occurred")
    user = models.ForeignKey(User, on_delete=models.PROTECT, help_text="User who performed the action")
    changes = models.JSONField(
        null=True, blank=True,
        help_text=(
            "Self-contained snapshot of the purchase state at the time of the action. "
            "CREATE: {'state': {...full purchase fields...}}. "
            "UPDATE: {'before': {...}, 'after': {...}, 'diff': {...changed fields only...}}. "
            "DELETE: {'final_state': {...full purchase fields...}}."
        ),
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP address of the user")

    def __str__(self) -> str:
        return f"{self.action} on Purchase #{self.purchase_id_snapshot} by {self.user.username} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['purchase_id_snapshot', '-timestamp']),
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


class DatabaseOperation(models.Model):
    """Tracks asynchronous PostgreSQL backup and restore operations."""
    TYPE_BACKUP = 'BACKUP'
    TYPE_RESTORE = 'RESTORE'
    TYPE_CHOICES = [
        (TYPE_BACKUP, 'Backup'),
        (TYPE_RESTORE, 'Restore'),
    ]

    STATUS_QUEUED = 'QUEUED'
    STATUS_RUNNING = 'RUNNING'
    STATUS_SUCCEEDED = 'SUCCEEDED'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_FAILED, 'Failed'),
    ]

    operation_type = models.CharField(max_length=10, choices=TYPE_CHOICES, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='database_operations',
        help_text='User that triggered this database operation.',
    )
    backup_filename = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Filename relative to media/backups.',
    )
    original_upload_name = models.CharField(max_length=255, blank=True, default='')
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    file_sha256 = models.CharField(max_length=64, blank=True, default='')
    is_pre_restore_backup = models.BooleanField(
        default=False,
        help_text='True for automatic safety backup created before a restore job.',
    )
    notes = models.TextField(blank=True, default='')
    output_log = models.TextField(blank=True, default='')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['operation_type', 'status']),
            models.Index(fields=['-created_at']),
        ]
        permissions = [
            ('manage_database_backups', 'Can run database backup and restore operations'),
        ]

    def __str__(self) -> str:
        suffix = ' (pre-restore)' if self.is_pre_restore_backup else ''
        return f"{self.operation_type} #{self.pk} {self.status}{suffix}"


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

