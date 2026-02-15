import csv
import json
from io import StringIO
from typing import Optional
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, permission_required
from django.core.mail import send_mail
from django.http import HttpResponseServerError, HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST, require_http_methods
from django.conf import settings

from iftf_duoverkoop.forms import OrderForm
from iftf_duoverkoop.models import Purchase
from iftf_duoverkoop.src import db
from iftf_duoverkoop.auth import (
    get_client_ip,
    log_purchase_action,
    can_edit_purchases,
    can_export_data
)
from iftf_duoverkoop.verification_codes import validate_code_format, normalize_code


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    Handle user login with custom login page.

    GET: Display login form
    POST: Authenticate user and redirect to intended page
    """
    if request.user.is_authenticated:
        return redirect('order')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '') or request.GET.get('next', '') or 'order'

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, _('login.success') % {'username': user.username})
            return redirect(next_url)
        else:
            error_message = _('login.error')
            return render(request, 'login.html', {
                'error_message': error_message,
                'next': next_url
            })

    next_url = request.GET.get('next', '')
    return render(request, 'login.html', {'next': next_url})


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    """Handle user logout and redirect to login page."""
    username = request.user.username
    auth_logout(request)
    messages.info(request, _('login.logout_success') % {'username': username})
    return redirect('login')


@login_required
def order(request: HttpRequest) -> HttpResponse:
    """Display the main order form with available performances."""
    if not db.data_ready():
        return HttpResponseServerError("The database has not been filled in correctly yet. Please notify a project "
                                       "administrator!")
    form = order_form(request, None, None)

    # Get performances with availability information
    performances_by_association = db.get_performances_by_association()

    # Add availability percentage and unique names to each association
    for association, performances in performances_by_association.items():
        # Add availability percentage to each performance
        for performance in performances:
            tickets_percentage = (performance.tickets_left() / performance.max_tickets) * 100
            performance.availability_percentage = tickets_percentage

        # Add unique performance names to the association
        unique_names = set()
        for performance in performances:
            unique_names.add(performance.name)
        association.unique_performance_names = sorted(list(unique_names))

    return render(request, 'order/order.html', {'form': form, 'performances': performances_by_association})


def order_form(request: HttpRequest, performance_1: Optional[str], performance_2: Optional[str]) -> OrderForm:
    """
    Process the order form and send confirmation email.

    Creates purchase record with audit trail when form is submitted.
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
                created_by=request.user
            )

            # Log the purchase creation
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
                    'created_at': purchase.date.isoformat()
                }
            )

            # Send confirmation email with verification code
            subject = _('email.subject')
            message = _('email.message_with_code') % {
                'name': purchase.name,
                'performance1': purchase.ticket1.selection(),
                'performance2': purchase.ticket2.selection(),
                'date': purchase.date.strftime('%d/%m/%Y %H:%M'),
                'verification_code': purchase.verification_code
            }

            if settings.SEND_EMAILS:
                send_mail(subject, message, "duoverkoop@iftf.be", [purchase.email])
                messages.success(request, _('orderpage.success_with_code') % {'code': purchase.verification_code})
            else:
                # Email sending disabled - show success message with code but don't send email
                messages.success(request, _('orderpage.success_with_code_no_email') % {'code': purchase.verification_code})

            form = OrderForm()
    else:
        initial = {}
        if performance_1:
            initial['performance1'] = performance_1
        if performance_2:
            initial['performance2'] = performance_2
        form = OrderForm(initial=initial)
    return form


@login_required
@permission_required('iftf_duoverkoop.view_purchase', raise_exception=True)
def purchase_history(request: HttpRequest) -> HttpResponse:
    """
    Display all purchases with search and filter capabilities.

    All authenticated users can view, but only Support Staff can edit.
    """
    # Get all purchases ordered by date descending (most recent first)
    purchases = Purchase.objects.all().order_by('-date')

    # Get available performances for filtering
    available_performances = db.get_readable_keyed_performances()

    # Get associations for filter dropdown
    associations = db.get_all_associations()

    # Check if user can edit purchases
    user_can_edit = can_edit_purchases(request.user)

    return render(request, 'purchase_history/purchase_history.html', {
        'purchases': purchases,
        'available_performances': available_performances,
        'associations': associations,
        'user_can_edit': user_can_edit
    })


@require_POST
@login_required
@permission_required('iftf_duoverkoop.change_purchase', raise_exception=True)
def edit_purchase(request: HttpRequest, purchase_id: int) -> JsonResponse:
    """
    Edit a purchase's name, email, and tickets (Support Staff only).

    All changes are logged to the audit trail.
    """
    try:
        data = json.loads(request.body)
        purchase = get_object_or_404(Purchase, id=purchase_id)

        # Store original values for audit log
        original_values = {
            'name': purchase.name,
            'email': purchase.email,
            'ticket1': purchase.ticket1.key,
            'ticket2': purchase.ticket2.key,
        }

        # Calculate original price
        original_price = purchase.ticket1.price + purchase.ticket2.price

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        ticket1_key = data.get('ticket1', '').strip()
        ticket2_key = data.get('ticket2', '').strip()

        if not name or not email:
            return JsonResponse({'success': False, 'error': _('error.name_email_required')}, status=400)

        # Track changes
        changes = {}
        if name != original_values['name']:
            changes['name'] = {'old': original_values['name'], 'new': name}
        if email != original_values['email']:
            changes['email'] = {'old': original_values['email'], 'new': email}

        # Calculate new price if tickets are being changed
        new_price = original_price
        if ticket1_key and ticket2_key:
            if ticket1_key == ticket2_key:
                return JsonResponse({'success': False, 'error': _('error.duplicate_performance')}, status=400)

            try:
                new_ticket1 = db.get_performance(ticket1_key)
                new_ticket2 = db.get_performance(ticket2_key)
                new_price = new_ticket1.price + new_ticket2.price
            except:
                return JsonResponse({'success': False, 'error': _('error.invalid_performance')}, status=400)

            # Check if performances are still available (accounting for current purchase)
            current_tickets1 = new_ticket1.tickets_left() + (1 if purchase.ticket1.key == ticket1_key else 0)
            current_tickets2 = new_ticket2.tickets_left() + (1 if purchase.ticket2.key == ticket2_key else 0)

            if current_tickets1 <= 0:
                return JsonResponse({'success': False, 'error': _('error.performance_no_longer_available') % {'performance': new_ticket1.selection(), 'number': 1}}, status=400)
            if current_tickets2 <= 0:
                return JsonResponse({'success': False, 'error': _('error.performance_no_longer_available') % {'performance': new_ticket2.selection(), 'number': 2}}, status=400)

            if ticket1_key != original_values['ticket1']:
                changes['ticket1'] = {'old': original_values['ticket1'], 'new': ticket1_key}
            if ticket2_key != original_values['ticket2']:
                changes['ticket2'] = {'old': original_values['ticket2'], 'new': ticket2_key}

            purchase.ticket1 = new_ticket1
            purchase.ticket2 = new_ticket2

        purchase.name = name
        purchase.email = email
        purchase.modified_by = request.user
        purchase.modified_date = datetime.now()
        purchase.save()

        # Log the edit action
        log_purchase_action(
            purchase=purchase,
            action='UPDATE',
            user=request.user,
            ip_address=get_client_ip(request),
            changes=changes
        )

        # Calculate price difference
        price_difference = new_price - original_price

        return JsonResponse({
            'success': True,
            'original_price': float(original_price),
            'new_price': float(new_price),
            'price_difference': float(price_difference)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
@permission_required('iftf_duoverkoop.delete_purchase', raise_exception=True)
def delete_purchase(request: HttpRequest, purchase_id: int) -> JsonResponse:
    """
    Delete a purchase (Support Staff only).

    Deletion is logged to the audit trail before the purchase is removed.
    """
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)

        # Log the deletion before removing the purchase
        log_purchase_action(
            purchase=purchase,
            action='DELETE',
            user=request.user,
            ip_address=get_client_ip(request),
            changes={
                'deleted_purchase': {
                    'id': purchase.id,
                    'name': purchase.name,
                    'email': purchase.email,
                    'ticket1': purchase.ticket1.key,
                    'ticket2': purchase.ticket2.key,
                    'verification_code': purchase.verification_code,
                    'created_by': purchase.created_by.username,
                    'created_at': purchase.date.isoformat()
                }
            }
        )

        purchase.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def export(request: HttpRequest) -> HttpResponse:
    """
    Export all purchases to CSV file grouped by association (Support Staff only).

    Access is restricted to Support Staff members only.
    """
    # Check if user has export permission
    if not can_export_data(request.user):
        return HttpResponse(_('error.no_permission'), status=403)

    # generate the file
    file = StringIO()
    writer = csv.writer(file)
    writer.writerow(['Date of Purchase', 'Performance', 'Date of Performance', 'Full Name', 'Email', 'Verification Code', 'Created By'])
    all_purchases = db.get_all_purchases()
    for association in db.get_all_associations():
        writer.writerows([[''], [association.name]])
        for purchase in all_purchases:
            # time format = 31/12/2024 12:00
            time_format = "%d/%m/%Y %H:%M"
            if purchase.ticket1.association == association:
                writer.writerow([purchase.date.strftime(time_format), purchase.ticket1.name,
                                 purchase.ticket1.date.strftime(time_format), purchase.name, purchase.email,
                                 purchase.verification_code, purchase.created_by.username])
            if purchase.ticket2.association == association:
                writer.writerow([purchase.date.strftime(time_format), purchase.ticket2.name,
                                 purchase.ticket2.date.strftime(time_format), purchase.name, purchase.email,
                                 purchase.verification_code, purchase.created_by.username])
    # create the response
    response = HttpResponse(file.getvalue(), content_type='application/csv')
    response['Content-Disposition'] = 'attachment; filename=export.csv'
    return response


@login_required
@permission_required('iftf_duoverkoop.change_purchase', raise_exception=True)
def verify_code(request: HttpRequest) -> HttpResponse:
    """
    Verification code lookup page (Support Staff only).

    Allows Support Staff to enter a three-word code and see purchase details.
    """
    purchase = None
    error_message = None
    code = None

    if request.method == 'POST':
        code = request.POST.get('verification_code', '').strip()

        if not code:
            error_message = _('verify.error_empty')
        elif not validate_code_format(code):
            error_message = _('verify.error_invalid_format')
        else:
            normalized_code = normalize_code(code)
            try:
                purchase = Purchase.objects.get(verification_code=normalized_code)
            except Purchase.DoesNotExist:
                error_message = _('verify.error_not_found')

    return render(request, 'verification/verify_code.html', {
        'purchase': purchase,
        'error_message': error_message,
        'code': code
    })


def main(request: HttpRequest) -> HttpResponse:
    """Redirect to the main order page."""
    return redirect(reverse('order'), permanent=True)


def db_info(request: HttpRequest) -> JsonResponse:
    """Return database type information."""
    from django.db import connection
    return JsonResponse({"database_type": connection.vendor})


def get_performances_by_association(request: HttpRequest, association_name: str) -> JsonResponse:
    """Return performances for a specific association."""
    try:
        association = db.get_association(association_name)
        performances = db.get_performances_by_association()[association]
        performance_data = [
            {
                'key': perf.key,
                'name': perf.selection()
            }
            for perf in performances
        ]
        return JsonResponse({'performances': performance_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_performance_prices(request: HttpRequest) -> JsonResponse:
    """Return prices for all available performances."""
    try:
        performances = db.get_all_performances()
        price_data = {
            perf.key: float(perf.price)
            for perf in performances
            if perf.tickets_left() > 0
        }
        return JsonResponse({'prices': price_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

