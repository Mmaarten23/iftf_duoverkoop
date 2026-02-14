import csv
from io import StringIO

from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponseServerError, HttpResponse, JsonResponse
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
            purchase = db.handle_purchase(clean['name'], clean['email'], clean['performance1'],
                               clean['performance2'])
            # Send confirmation email
            subject = _('email.subject')
            message = _('email.message') % {
                'name': purchase.name,
                'performance1': purchase.ticket1.selection(),
                'performance2': purchase.ticket2.selection(),
                'date': purchase.date.strftime('%d/%m/%Y %H:%M')
            }
            send_mail(subject, message, None, [purchase.email])
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


def export(request):
    # generate the file
    file = StringIO()
    writer = csv.writer(file)
    writer.writerow(['Date of Purchase', 'Performance', 'Date of Performance', 'Full Name', 'Email'])
    all_purchases = db.get_all_purchases()
    for association in db.get_all_associations():
        writer.writerows([[''], [association.name]])
        for purchase in all_purchases:
            # time format = 31/12/2024 12:00
            time_format = "%d/%m/%Y %H:%M"
            if purchase.ticket1.association == association:
                writer.writerow([purchase.date.strftime(time_format), purchase.ticket1.name,
                                 purchase.ticket1.date.strftime(time_format), purchase.name, purchase.email])
            if purchase.ticket2.association == association:
                writer.writerow([purchase.date.strftime(time_format), purchase.ticket2.name,
                                 purchase.ticket2.date.strftime(time_format), purchase.name, purchase.email])
    # create the response
    response = HttpResponse(file.getvalue(), content_type='application/csv')
    response['Content-Disposition'] = 'attachment; filename=export.csv'
    return response


def main(request):
    return redirect(reverse('order'), permanent=True)


def db_info(request):
    from django.db import connection
    return JsonResponse({"database_type": connection.vendor})
