"""
core/admin.py – Django admin registrations for all models.
"""
from django.contrib import admin
from django import forms
import os
from django.conf import settings

from iftf_duoverkoop.src.core.models import Association, AssociationRepProfile, Performance, Purchase, PurchaseAuditLog, LoginAuditLog


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

