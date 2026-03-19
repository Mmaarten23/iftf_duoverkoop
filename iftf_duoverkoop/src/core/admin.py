"""
core/admin.py – Django admin registrations for all models.
"""
from django.contrib import admin
from django import forms
import os
from django.conf import settings

from iftf_duoverkoop.src.core.models import (
    Address,
    Association,
    AssociationRepProfile,
    DatabaseOperation,
    EmailCampaign,
    EmailCampaignRecipient,
    EmailTemplateSettings,
    Performance,
    Purchase,
    PurchaseAuditLog,
    LoginAuditLog,
)


class AssociationAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        media_path = os.path.join(settings.BASE_DIR, 'iftf_duoverkoop', 'media', 'associations')
        choices = [('', 'No image')]
        if os.path.exists(media_path):
            files = [f for f in os.listdir(media_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            choices += [(os.path.join('associations', f), f) for f in sorted(files)]
        self.fields['image'].widget = forms.Select(choices=choices)

    class Meta:
        model = Association
        fields = '__all__'


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    form = AssociationAdminForm
    list_display = ['name', 'address', 'image']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['street', 'house_number', 'box', 'postal_code', 'city', 'country']
    search_fields = ['street', 'city', 'postal_code']


@admin.register(AssociationRepProfile)
class AssociationRepProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'association']
    list_filter = ['association']
    search_fields = ['user__username', 'association__name']
    autocomplete_fields = []


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ['key', 'association', 'name', 'date', 'price', 'max_tickets']
    list_filter = ['association']
    search_fields = ['key', 'name']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'ticket1', 'ticket2', 'date', 'created_by', 'email_status']
    list_filter = ['date', 'ticket1__association', 'email_status']
    search_fields = ['name', 'email', 'verification_code']
    readonly_fields = ['verification_code', 'created_by', 'date', 'email_status']


@admin.register(PurchaseAuditLog)
class PurchaseAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for purchase audit logs — read-only for security."""
    list_display = ['id', 'action', 'purchase', 'user', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['purchase__id', 'user__username', 'ip_address']
    readonly_fields = ['purchase', 'action', 'user', 'timestamp', 'changes', 'ip_address']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LoginAuditLog)
class LoginAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for login audit logs — read-only for security."""
    list_display = ['id', 'event', 'username', 'user', 'timestamp', 'ip_address']
    list_filter = ['event', 'timestamp']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['event', 'username', 'user', 'timestamp', 'ip_address']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DatabaseOperation)
class DatabaseOperationAdmin(admin.ModelAdmin):
    """Read-only admin listing for backup/restore jobs."""
    list_display = [
        'id', 'operation_type', 'status', 'created_by', 'created_at',
        'started_at', 'finished_at', 'is_pre_restore_backup',
    ]
    list_filter = ['operation_type', 'status', 'is_pre_restore_backup', 'created_at']
    search_fields = ['id', 'created_by__username', 'backup_filename', 'original_upload_name']
    readonly_fields = [
        'operation_type', 'status', 'created_at', 'started_at', 'finished_at',
        'created_by', 'backup_filename', 'original_upload_name', 'file_size_bytes',
        'file_sha256', 'is_pre_restore_backup', 'notes', 'output_log', 'error_message',
    ]
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EmailTemplateSettings)
class EmailTemplateSettingsAdmin(admin.ModelAdmin):
    list_display = ['singleton_key', 'updated_at', 'updated_by']
    readonly_fields = ['singleton_key', 'updated_at', 'updated_by']
    fieldsets = (
        ('Templates', {
            'fields': ('subject_template', 'text_template', 'html_template'),
        }),
        ('Styling', {
            'fields': (
                'primary_color', 'accent_color', 'background_color',
                'card_background_color', 'border_color', 'content_width', 'footer_text',
            ),
        }),
        ('Audit', {
            'fields': ('singleton_key', 'updated_at', 'updated_by'),
        }),
    )

    def has_add_permission(self, request):
        return not EmailTemplateSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'audience_type', 'status', 'total_recipients',
        'sent_count', 'failed_count', 'created_by', 'created_at',
    ]
    list_filter = ['audience_type', 'status', 'created_at']
    search_fields = ['name', 'created_by__username']
    readonly_fields = [
        'created_at', 'started_at', 'finished_at',
        'status', 'total_recipients', 'sent_count', 'failed_count', 'error_message',
    ]


@admin.register(EmailCampaignRecipient)
class EmailCampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'email', 'customer_name', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['email', 'customer_name', 'campaign__name']
    readonly_fields = [
        'campaign', 'purchase', 'email', 'customer_name',
        'status', 'sent_at', 'error_message', 'audience_context',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


