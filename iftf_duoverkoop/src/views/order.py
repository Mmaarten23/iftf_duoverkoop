"""
views/order.py – Order page: display form, process purchase, prefill helper.
"""
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponseServerError, HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from iftf_duoverkoop.src.forms.order import OrderForm
from iftf_duoverkoop.src import db
from iftf_duoverkoop.src.core.auth import get_client_ip, log_purchase_action


@login_required
@require_http_methods(["GET", "POST"])
def order(request: HttpRequest) -> HttpResponse:
    """Display the main order form with available performances."""
    if not db.data_ready():
        return HttpResponseServerError(
            "The database has not been filled in correctly yet. "
            "Please notify a project administrator!"
        )

    form = _process_order_form(request, None, None)
    performances_by_association = db.get_performances_by_association()

    for association, performances in performances_by_association.items():
        for performance in performances:
            performance.availability_percentage = (
                performance.tickets_left() / performance.max_tickets * 100
            )
        unique_names = sorted({p.name for p in performances})
        association.unique_performance_names = unique_names

    return render(request, 'order/order.html', {
        'form': form,
        'performances': performances_by_association,
    })


def _process_order_form(
    request: HttpRequest,
    performance_1: Optional[str],
    performance_2: Optional[str],
) -> OrderForm:
    """
    Process the order form on POST; build an empty/pre-filled form on GET.

    Creates a Purchase record with a full audit trail on valid submission.
    """
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            clean = form.cleaned_data
            purchase = db.handle_purchase(
                clean['name'],
                clean['email'],
                clean['performance1'],
                clean['performance2'],
                created_by=request.user,
            )

            log_purchase_action(
                purchase=purchase,
                action='CREATE',
                user=request.user,
                ip_address=get_client_ip(request),
                changes={
                    'name': purchase.name,
                    'email': purchase.email,
                    'ticket1': purchase.ticket1.key,
                    'ticket2': purchase.ticket2.key,
                    'verification_code': purchase.verification_code,
                    'created_at': purchase.date.isoformat(),
                },
            )

            subject = _('email.subject')
            message = _('email.message_with_code') % {
                'name': purchase.name,
                'performance1': purchase.ticket1.selection(),
                'performance2': purchase.ticket2.selection(),
                'date': purchase.date.strftime('%d/%m/%Y %H:%M'),
                'verification_code': purchase.verification_code,
            }
            if settings.SEND_EMAILS:
                send_mail(subject, message, "duoverkoop@iftf.be", [purchase.email])
                messages.success(request, _('orderpage.success_with_code') % {'code': purchase.verification_code})
            else:
                messages.success(
                    request,
                    _('orderpage.success_with_code_no_email') % {'code': purchase.verification_code},
                )

            request.session['last_customer'] = {'name': purchase.name, 'email': purchase.email}
            return OrderForm()
    else:
        initial = {}
        if performance_1:
            initial['performance1'] = performance_1
        if performance_2:
            initial['performance2'] = performance_2
        form = OrderForm(initial=initial)
    return form


def main(request: HttpRequest) -> HttpResponse:
    """Redirect root URL to the order page."""
    return redirect(reverse('order'), permanent=True)


@login_required
def get_last_customer(request: HttpRequest) -> JsonResponse:
    """Return the name/email stored in this session from the last order."""
    last = request.session.get('last_customer')
    if last:
        return JsonResponse({'found': True, 'name': last['name'], 'email': last['email']})
    return JsonResponse({'found': False})

