"""
views/history.py – Purchase history, edit, delete, and resend-email views.
"""
import json
import re
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from iftf_duoverkoop.src.core.models import Purchase
from iftf_duoverkoop.src.core.auth import get_client_ip, log_purchase_action, can_edit_purchases
from iftf_duoverkoop.src.core.email import send_confirmation_email_async, build_confirmation_message
from iftf_duoverkoop.src import db

STUDENT_ID_RE = re.compile(r'^r\d{7}$', re.IGNORECASE)


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
        'send_emails_enabled': settings.SEND_EMAILS,
        'email_status_choices': Purchase.EMAIL_STATUS_CHOICES,
    })


@require_POST
@login_required
@permission_required('iftf_duoverkoop.change_purchase', raise_exception=True)
def edit_purchase(request: HttpRequest, purchase_id: int) -> JsonResponse:
    """Edit a purchase's name, email, tickets, and culture-card status (Support Staff only)."""
    try:
        data = json.loads(request.body)
        purchase = get_object_or_404(Purchase, id=purchase_id)

        original = {
            'name': purchase.name,
            'email': purchase.email,
            'ticket1': purchase.ticket1.key,
            'ticket2': purchase.ticket2.key,
            'has_culture_card': purchase.has_culture_card,
            'student_id': purchase.student_id,
        }
        original_price = purchase.total_price()

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        ticket1_key = data.get('ticket1', '').strip()
        ticket2_key = data.get('ticket2', '').strip()
        has_culture_card = bool(data.get('has_culture_card', False))
        student_id = data.get('student_id', '').strip()

        if not name or not email:
            return JsonResponse({'success': False, 'error': _('error.name_email_required')}, status=400)

        # Validate student ID when culture card is ticked
        if has_culture_card:
            if not student_id:
                return JsonResponse({'success': False, 'error': _('error.student_id_required')}, status=400)
            if not STUDENT_ID_RE.match(student_id):
                return JsonResponse({'success': False, 'error': _('error.student_id_invalid')}, status=400)

        diff = {}
        if name != original['name']:
            diff['name'] = {'old': original['name'], 'new': name}
        if email != original['email']:
            diff['email'] = {'old': original['email'], 'new': email}
        if has_culture_card != original['has_culture_card']:
            diff['has_culture_card'] = {'old': original['has_culture_card'], 'new': has_culture_card}
        if student_id != original['student_id']:
            diff['student_id'] = {'old': original['student_id'], 'new': student_id}

        new_ticket1 = purchase.ticket1
        new_ticket2 = purchase.ticket2
        if ticket1_key and ticket2_key:
            if ticket1_key == ticket2_key:
                return JsonResponse({'success': False, 'error': _('error.duplicate_performance')}, status=400)
            try:
                new_ticket1 = db.get_performance(ticket1_key)
                new_ticket2 = db.get_performance(ticket2_key)
            except Exception:
                return JsonResponse({'success': False, 'error': _('error.invalid_performance')}, status=400)

            t1_avail = new_ticket1.tickets_left() + (1 if purchase.ticket1.key == ticket1_key else 0)
            t2_avail = new_ticket2.tickets_left() + (1 if purchase.ticket2.key == ticket2_key else 0)
            if t1_avail <= 0:
                return JsonResponse({'success': False, 'error': _('error.performance_no_longer_available') % {'performance': new_ticket1.selection(), 'number': 1}}, status=400)
            if t2_avail <= 0:
                return JsonResponse({'success': False, 'error': _('error.performance_no_longer_available') % {'performance': new_ticket2.selection(), 'number': 2}}, status=400)

            if ticket1_key != original['ticket1']:
                diff['ticket1'] = {'old': original['ticket1'], 'new': ticket1_key}
            if ticket2_key != original['ticket2']:
                diff['ticket2'] = {'old': original['ticket2'], 'new': ticket2_key}

            purchase.ticket1 = new_ticket1
            purchase.ticket2 = new_ticket2

        # Capture the before-state while the purchase object still holds old values
        before_state = {
            'name': original['name'],
            'email': original['email'],
            'ticket1': original['ticket1'],
            'ticket2': original['ticket2'],
            'has_culture_card': original['has_culture_card'],
            'student_id': original['student_id'],
        }

        purchase.name = name
        purchase.email = email
        purchase.has_culture_card = has_culture_card
        purchase.student_id = student_id if has_culture_card else ''
        purchase.modified_by = request.user
        purchase.modified_date = datetime.now()
        purchase.save()

        # Compute new price using updated purchase state
        new_price = purchase.total_price()

        after_state = {
            'name': purchase.name,
            'email': purchase.email,
            'ticket1': purchase.ticket1.key,
            'ticket2': purchase.ticket2.key,
            'has_culture_card': purchase.has_culture_card,
            'student_id': purchase.student_id,
        }

        log_purchase_action(
            purchase=purchase, action='UPDATE',
            user=request.user, ip_address=get_client_ip(request),
            changes={
                'before': before_state,
                'after': after_state,
                'diff': diff,
            },
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
    """
    Delete a purchase (Support Staff only).

    The full final state is captured as an audit log entry before the row is
    removed.  Because PurchaseAuditLog.purchase is SET_NULL, the log entry
    survives the deletion and remains queryable via purchase_id_snapshot.
    """
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)
        # log_purchase_action auto-builds {'final_state': <snapshot>} for DELETE
        log_purchase_action(
            purchase=purchase, action='DELETE',
            user=request.user, ip_address=get_client_ip(request),
        )
        purchase.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
@permission_required('iftf_duoverkoop.change_purchase', raise_exception=True)
def resend_email(request: HttpRequest, purchase_id: int) -> JsonResponse:
    """
    Resend the confirmation email for a purchase.

    Always allowed regardless of current email_status. The caller should
    warn the user first when the status is already SENT (handled on the
    front end via a confirmation dialog).

    Returns JSON:
        { "success": true, "already_sent": <bool> }   on dispatch
        { "success": false, "error": "…" }             on error
    """
    if not settings.SEND_EMAILS:
        return JsonResponse(
            {'success': False, 'error': _('purchase_history.resend_email_disabled')},
            status=400,
        )
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)
        already_sent = purchase.email_status == Purchase.EMAIL_SENT
        subject, message = build_confirmation_message(purchase)
        send_confirmation_email_async(purchase, subject, message)
        return JsonResponse({'success': True, 'already_sent': already_sent})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

