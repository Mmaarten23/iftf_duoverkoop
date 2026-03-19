"""
dashboard/forms.py – Forms used exclusively by the staff dashboard.
"""
import os
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from iftf_duoverkoop.src.core.models import Association, EmailCampaign, EmailTemplateSettings, Performance
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
    discounted_price = forms.FloatField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Discounted price – culture card (€)',
        help_text='Leave blank if no culture-card discount applies.',
    )
    max_tickets = forms.IntegerField(
        min_value=0,
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

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get('price')
        discounted = cleaned.get('discounted_price')
        if price is not None and discounted is not None and discounted >= price:
            self.add_error('discounted_price', 'Discounted price must be lower than the regular price.')
        return cleaned


class BulkSetPriceForm(forms.Form):
    """Form used for the two 'set all prices at once' management operations."""
    price = forms.FloatField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='New price (€)',
    )


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


class RestoreDatabaseForm(forms.Form):
    backup_file = forms.FileField(
        label='Backup file (.dump)',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.dump,application/octet-stream'}),
    )
    confirmation = forms.CharField(
        label='Type RESTORE to confirm',
        max_length=32,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RESTORE'}),
        help_text='This operation is destructive and should only be used during planned maintenance.',
    )

    def clean_confirmation(self):
        value = (self.cleaned_data.get('confirmation') or '').strip().upper()
        if value != 'RESTORE':
            raise ValidationError('Please type RESTORE exactly to confirm.')
        return value


class EmailTemplateSettingsForm(forms.ModelForm):
    class Meta:
        model = EmailTemplateSettings
        fields = [
            'subject_template',
            'text_template',
            'html_template',
            'primary_color',
            'accent_color',
            'background_color',
            'card_background_color',
            'border_color',
            'content_width',
            'footer_text',
        ]
        widgets = {
            'subject_template': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'text_template': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'html_template': forms.Textarea(attrs={
                'class': 'form-control font-monospace email-html-editor',
                'rows': 22,
                'spellcheck': 'false',
                'autocapitalize': 'off',
                'autocomplete': 'off',
                'autocorrect': 'off',
            }),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'background_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'card_background_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'border_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'content_width': forms.NumberInput(attrs={'class': 'form-control', 'min': 360, 'max': 900}),
            'footer_text': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EmailCampaignForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label=_('dashboard.email.campaign_name'),
    )
    audience_type = forms.ChoiceField(
        choices=EmailCampaign.AUDIENCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_campaign_audience_type'}),
        label=_('dashboard.email.audience'),
    )
    associations = forms.ModelMultipleChoiceField(
        queryset=Association.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '6', 'id': 'id_campaign_associations'}),
        label=_('dashboard.email.associations'),
        help_text=_('dashboard.email.associations_help'),
    )
    performance = forms.ModelChoiceField(
        queryset=Performance.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_campaign_performance'}),
        label=_('dashboard.email.performance'),
        help_text=_('dashboard.email.performance_help'),
    )
    subject_template = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label=_('dashboard.email.subject_template'),
    )
    text_template = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
        label=_('dashboard.email.text_body'),
    )
    html_template = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace email-html-editor',
            'rows': 12,
            'spellcheck': 'false',
            'autocomplete': 'off',
        }),
        label=_('dashboard.email.html_body'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['associations'].queryset = Association.objects.order_by('name')
        self.fields['performance'].queryset = Performance.objects.select_related('association').order_by('date')
        self.fields['performance'].label_from_instance = lambda p: f'{p.association.name} - {p.selection()}'

    def clean(self):
        cleaned = super().clean()
        audience_type = cleaned.get('audience_type')
        associations = cleaned.get('associations')
        performance = cleaned.get('performance')

        if audience_type == EmailCampaign.AUDIENCE_ASSOCIATIONS and not associations:
            self.add_error('associations', _('dashboard.email.associations_required'))
        if audience_type == EmailCampaign.AUDIENCE_PERFORMANCE and not performance:
            self.add_error('performance', _('dashboard.email.performance_required'))

        if not cleaned.get('text_template') and not cleaned.get('html_template'):
            self.add_error('text_template', _('dashboard.email.body_required'))
        return cleaned


