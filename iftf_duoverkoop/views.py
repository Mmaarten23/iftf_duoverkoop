from django.contrib import messages
from django.http import HttpResponseServerError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from iftf_duoverkoop.forms import OrderForm
from iftf_duoverkoop.src import db


def order(request):
    if not db.data_ready():
        return HttpResponseServerError("The database has not been filled in correctly yet. Please notify a project "
                                       "administrator!")
    performance_1 = request.GET.get('performance_1')
    performance_2 = request.GET.get('performance_2')
    form = order_form(request, performance_1, performance_2)
    return render(request, 'order/order.html', {'form': form, 'performances': db.get_performances_by_association()})


def order_form(request, performance_1, performance_2):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            clean = form.cleaned_data
            db.handle_purchase(clean['first_name'], clean['last_name'], clean['email'], clean['performance1'],
                               clean['performance2'])
            messages.success(request, _('orderpage.success'))
            form = OrderForm()
    else:
        initial = {}
        if performance_1:
            initial['performance1'] = performance_1
        if performance_2:
            initial['performance2'] = performance_2
        form = OrderForm(initial=initial)
    return form


def purchase_history(request):
    return render(request, 'purchase_history/purchase_history.html', {'purchases': db.get_all_purchases()})


def main(request):
    return redirect(reverse('order'), permanent=True)
