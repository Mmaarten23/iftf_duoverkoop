from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from iftf_duoverkoop.src import db


class OrderForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        performances = db.get_readable_keyed_performances()
        performances.insert(0, ('', ''))

        self.fields['performance1'].choices = performances
        self.fields['performance2'].choices = performances

    first_name = forms.CharField(label=_('person.name_first'), max_length=100)
    last_name = forms.CharField(label=_('person.name_last'), max_length=100)
    performance1 = forms.ChoiceField(label=_('performance.name'), choices=[])
    performance2 = forms.ChoiceField(label=_('performance.name'), choices=[])

    error_duplicate_performance = _('error.duplicate_performance')
    error_empty_field = _('error.empty_field')
    error_sold_out = _('error.sold_out')

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if not first_name:
            raise ValidationError(_(self.error_empty_field))
        return first_name.strip()[0].upper() + first_name.strip()[1:]

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']
        if not last_name:
            raise ValidationError(_(self.error_empty_field))
        return last_name.strip()[0].upper() + last_name.strip()[1:]

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

    def clean(self):
        cleaned_data = super().clean()
        key_1 = cleaned_data.get('performance1')
        key_2 = cleaned_data.get('performance2')

        if key_1 and key_2:
            performance_1 = db.get_performance(key_1)
            performance_2 = db.get_performance(key_2)
            if performance_1 == performance_2:
                raise ValidationError(self.error_duplicate_performance)
