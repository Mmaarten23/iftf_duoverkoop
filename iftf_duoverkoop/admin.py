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
