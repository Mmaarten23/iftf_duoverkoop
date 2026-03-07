"""
dashboard/forms.py – Forms used exclusively by the staff dashboard.
"""
import os
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from iftf_duoverkoop.src.core.models import Association, Performance
from iftf_duoverkoop.src.core.auth import GROUP_POS_STAFF, GROUP_SUPPORT_STAFF, GROUP_ASSOCIATION_REP


def _logo_choices():
    """Return (value, label) choices for logo files in media/associations/."""
    media_path = os.path.join(settings.BASE_DIR, 'iftf_duoverkoop', 'media', 'associations')
    choices = [('', '— No image —')]
    if os.path.exists(media_path):
        files = sorted(
            f for f in os.listdir(media_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
        )
        choices += [(os.path.join('associations', f), f) for f in files]
    return choices


class AssociationForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Name',
    )
    image = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Logo',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].choices = _logo_choices()

    def clean_name(self):
        return self.cleaned_data['name'].strip()


class PerformanceForm(forms.Form):
    key = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. wina-2026-comedy'}),
        label='Key (unique identifier)',
    )
    name = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Performance name',
    )
    association = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Association',
    )
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label='Date & time',
        input_formats=['%Y-%m-%dT%H:%M'],
    )
    price = forms.FloatField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Price (€)',
    )
    max_tickets = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Maximum tickets',
    )

    def __init__(self, *args, editing_key=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._editing_key = editing_key
        self.fields['association'].choices = [('', '— Select association —')] + [
            (a.name, a.name) for a in Association.objects.order_by('name')
        ]

    def clean_key(self):
        key = self.cleaned_data['key'].strip()
        qs = Performance.objects.filter(key=key)
        if self._editing_key:
            qs = qs.exclude(key=self._editing_key)
        if qs.exists():
            raise ValidationError('A performance with this key already exists.')
        return key


GROUP_CHOICES = [
    ('', '— No group —'),
    (GROUP_POS_STAFF, GROUP_POS_STAFF),
    (GROUP_SUPPORT_STAFF, GROUP_SUPPORT_STAFF),
    (GROUP_ASSOCIATION_REP, GROUP_ASSOCIATION_REP),
]


class CreateUserForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
    )
    is_staff = forms.BooleanField(
        required=False,
        label='Staff / dashboard access',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    group = forms.ChoiceField(
        choices=GROUP_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_group'}),
        label='Role group',
    )
    association = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_association'}),
        label='Association (for representatives)',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['association'].choices = [('', '— Select association —')] + [
            (a.name, a.name) for a in Association.objects.order_by('name')
        ]

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('group') == GROUP_ASSOCIATION_REP and not cleaned.get('association'):
            self.add_error('association', 'An association must be selected for Association Representatives.')
        return cleaned


class EditUserForm(forms.Form):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    is_staff = forms.BooleanField(
        required=False,
        label='Staff / dashboard access',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    is_active = forms.BooleanField(
        required=False,
        label='Active (can log in)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    group = forms.ChoiceField(
        choices=GROUP_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_group'}),
        label='Role group',
    )
    association = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_association'}),
        label='Association (for representatives)',
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        min_length=8,
        label='New password (leave blank to keep current)',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['association'].choices = [('', '— Select association —')] + [
            (a.name, a.name) for a in Association.objects.order_by('name')
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('group') == GROUP_ASSOCIATION_REP and not cleaned.get('association'):
            self.add_error('association', 'An association must be selected for Association Representatives.')
        return cleaned


class LogoUploadForm(forms.Form):
    logo = forms.ImageField(
        label='Logo file (.jpg / .png / .gif)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
    )

