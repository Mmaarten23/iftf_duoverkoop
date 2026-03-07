"""
views/history.py – Purchase history, edit, and delete views.
"""
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from iftf_duoverkoop.src.core.models import Purchase
from iftf_duoverkoop.src.core.auth import get_client_ip, log_purchase_action, can_edit_purchases
from iftf_duoverkoop.src import db


@login_required
@permission_required('iftf_duoverkoop.view_purchase', raise_exception=True)
def purchase_history(request: HttpRequest) -> HttpResponse:
    """
    Display all purchases with search and filter capabilities.

    All users with view_purchase can see the list.
    Edit/delete controls are only shown when the user also has change_purchase.
    """
    return render(request, 'purchase_history/purchase_history.html', {
        'purchases': Purchase.objects.all().order_by('-date'),
        'available_performances': db.get_readable_keyed_performances(),
        'associations': db.get_all_associations(),
        'user_can_edit': can_edit_purchases(request.user),
    })


@require_POST
@login_required
@permission_required('iftf_duoverkoop.change_purchase', raise_exception=True)
def edit_purchase(request: HttpRequest, purchase_id: int) -> JsonResponse:
    """Edit a purchase's name, email, and tickets (Support Staff only)."""
    try:
        data = json.loads(request.body)
        purchase = get_object_or_404(Purchase, id=purchase_id)

        original = {
            'name': purchase.name,
            'email': purchase.email,
            'ticket1': purchase.ticket1.key,
            'ticket2': purchase.ticket2.key,
        }
        original_price = purchase.ticket1.price + purchase.ticket2.price

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        ticket1_key = data.get('ticket1', '').strip()
        ticket2_key = data.get('ticket2', '').strip()

        if not name or not email:
            return JsonResponse({'success': False, 'error': _('error.name_email_required')}, status=400)

        changes = {}
        if name != original['name']:
            changes['name'] = {'old': original['name'], 'new': name}
        if email != original['email']:
            changes['email'] = {'old': original['email'], 'new': email}

        new_price = original_price
        if ticket1_key and ticket2_key:
            if ticket1_key == ticket2_key:
                return JsonResponse({'success': False, 'error': _('error.duplicate_performance')}, status=400)
            try:
                new_ticket1 = db.get_performance(ticket1_key)
                new_ticket2 = db.get_performance(ticket2_key)
                new_price = new_ticket1.price + new_ticket2.price
            except Exception:
                return JsonResponse({'success': False, 'error': _('error.invalid_performance')}, status=400)

            t1_avail = new_ticket1.tickets_left() + (1 if purchase.ticket1.key == ticket1_key else 0)
            t2_avail = new_ticket2.tickets_left() + (1 if purchase.ticket2.key == ticket2_key else 0)
            if t1_avail <= 0:
                return JsonResponse({'success': False, 'error': _('error.performance_no_longer_available') % {'performance': new_ticket1.selection(), 'number': 1}}, status=400)
            if t2_avail <= 0:
                return JsonResponse({'success': False, 'error': _('error.performance_no_longer_available') % {'performance': new_ticket2.selection(), 'number': 2}}, status=400)

            if ticket1_key != original['ticket1']:
                changes['ticket1'] = {'old': original['ticket1'], 'new': ticket1_key}
            if ticket2_key != original['ticket2']:
                changes['ticket2'] = {'old': original['ticket2'], 'new': ticket2_key}

            purchase.ticket1 = new_ticket1
            purchase.ticket2 = new_ticket2

        purchase.name = name
        purchase.email = email
        purchase.modified_by = request.user
        purchase.modified_date = datetime.now()
        purchase.save()

        log_purchase_action(
            purchase=purchase, action='UPDATE',
            user=request.user, ip_address=get_client_ip(request), changes=changes,
        )

        price_difference = new_price - original_price
        return JsonResponse({
            'success': True,
            'original_price': float(original_price),
            'new_price': float(new_price),
            'price_difference': float(price_difference),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
@permission_required('iftf_duoverkoop.delete_purchase', raise_exception=True)
def delete_purchase(request: HttpRequest, purchase_id: int) -> JsonResponse:
    """Delete a purchase (Support Staff only). Deletion is logged before removal."""
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)
        log_purchase_action(
            purchase=purchase, action='DELETE',
            user=request.user, ip_address=get_client_ip(request),
            changes={'deleted_purchase': {
                'id': purchase.id, 'name': purchase.name, 'email': purchase.email,
                'ticket1': purchase.ticket1.key, 'ticket2': purchase.ticket2.key,
                'verification_code': purchase.verification_code,
                'created_by': purchase.created_by.username,
                'created_at': purchase.date.isoformat(),
            }},
        )
        purchase.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

