"""
forms/order.py – Order form for ticket purchasing.
"""
import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from iftf_duoverkoop.src import db

STUDENT_ID_RE = re.compile(r'^r\d{7}$', re.IGNORECASE)


class OrderForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        performances = db.get_readable_keyed_performances()
        performances.sort(key=lambda x: x[1].lower())
        performances.insert(0, ('', ''))
        self.fields['performance1'].choices = performances
        self.fields['performance2'].choices = performances

    name = forms.CharField(label=_('person.name'), max_length=100)
    email = forms.EmailField(label=_('person.email'))
    performance1 = forms.ChoiceField(label=_('performance.name'), choices=[])
    performance2 = forms.ChoiceField(label=_('performance.name'), choices=[])
    has_culture_card = forms.BooleanField(
        label=_('orderpage.has_culture_card'),
        required=False,
    )
    student_id = forms.CharField(
        label=_('orderpage.student_id'),
        max_length=20,
        required=False,
        help_text=_('orderpage.student_id_hint'),
    )

    error_duplicate_performance = _('error.duplicate_performance')
    error_empty_field = _('error.empty_field')
    error_sold_out = _('error.sold_out')

    def clean_name(self):
        first_name = self.cleaned_data['name']
        if not first_name:
            raise ValidationError(_(self.error_empty_field))
        return first_name.strip()[0].upper() + first_name.strip()[1:]

    def clean_performance1(self):
        key = self.cleaned_data['performance1']
        if not key:
            raise ValidationError(_(self.error_empty_field))
        if db.get_performance(key) is None:
            raise ValidationError(_(self.error_empty_field))
        if db.get_performance(key).tickets_left() <= 0:
            raise ValidationError(_(self.error_sold_out))
        return key

    def clean_performance2(self):
        key = self.cleaned_data['performance2']
        if not key:
            return None
        if db.get_performance(key) is None:
            raise ValidationError(_(self.error_empty_field))
        if db.get_performance(key).tickets_left() <= 0:
            raise ValidationError(_(self.error_sold_out))
        return key

    def clean_student_id(self):
        sid = self.cleaned_data.get('student_id', '').strip()
        return sid

    def clean(self):
        cleaned_data = super().clean()
        key_1 = cleaned_data.get('performance1')
        key_2 = cleaned_data.get('performance2')
        if key_1 and key_2:
            if db.get_performance(key_1) == db.get_performance(key_2):
                raise ValidationError(self.error_duplicate_performance)

        has_card = cleaned_data.get('has_culture_card', False)
        student_id = cleaned_data.get('student_id', '').strip()
        if has_card:
            if not student_id:
                self.add_error('student_id', _('error.student_id_required'))
            elif not STUDENT_ID_RE.match(student_id):
                self.add_error('student_id', _('error.student_id_invalid'))
        return cleaned_data
