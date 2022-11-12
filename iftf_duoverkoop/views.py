from datetime import datetime

from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from iftf_duoverkoop.forms import OrderForm
from iftf_duoverkoop.src import db


def order(request):
    form = order_form(request)
    return render(request, 'order/order.html', {'form': form, 'performances': db.get_performances_by_association()})


def order_form(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            clean = form.cleaned_data
            db.handle_purchase(clean['first_name'], clean['last_name'], clean['performance1'], clean['performance2'])
            messages.success(request, _('orderpage.success'))
            form = OrderForm()
    else:
        form = OrderForm()
    return form


def purchase_history(request):
    return render(request, 'purchase_history/purchase_history.html', {'purchases': db.get_all_purchases()})


def main(request):
    return redirect(reverse('order'), permanent=True)


def _DEBUG_load_db():
    db.create_association('Wina')
    db.create_association('Politika')
    db.create_performance(
        key="Wina1104",
        date=datetime(2022, 4, 11),
        association=db.get_association('Wina'),
        name="Van je familie moet je het maar hebben",
        price=5,
        tickets=30
    )
    db.create_performance(
        key="Politika0104",
        date=datetime(2022, 4, 1),
        association=db.get_association('Politika'),
        name="Working title",
        price=5,
        tickets=30
    )
    db.create_performance(
        key="Politika0304",
        date=datetime(2022, 4, 3),
        association=db.get_association('Politika'),
        name="Working title",
        price=5,
        tickets=30
    )
    db.create_performance(
        key="Politika0504",
        date=datetime(2022, 4, 5),
        association=db.get_association('Politika'),
        name="Working title",
        price=5,
        tickets=30
    )

