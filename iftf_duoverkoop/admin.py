from django.contrib import admin
from django import forms
import os
from django.conf import settings
from iftf_duoverkoop.models import *


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


class AssociationAdmin(admin.ModelAdmin):
    form = AssociationAdminForm


admin.site.register(Performance)
admin.site.register(Purchase)
admin.site.register(Association, AssociationAdmin)


@admin.register(PurchaseAuditLog)
class PurchaseAuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for audit logs - read-only for security.
    """
    list_display = ['id', 'action', 'purchase', 'user', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['purchase_id', 'user__username', 'ip_address']
    readonly_fields = ['purchase', 'action', 'user', 'timestamp', 'changes', 'ip_address']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        """Audit logs cannot be manually added."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs cannot be deleted (append-only)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs cannot be modified."""
        return False

