"""
dashboard/views.py – Staff management dashboard views.

All views require login + is_staff=True (enforced by @staff_required).
"""
import os
import json
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST, require_http_methods

from iftf_duoverkoop.src.core.models import Association, Performance, Purchase, PurchaseAuditLog, LoginAuditLog
from iftf_duoverkoop.src.core.auth import setup_permission_groups
from iftf_duoverkoop.src.dashboard.forms import (
    AssociationForm, PerformanceForm, CreateUserForm, EditUserForm, LogoUploadForm,
)


# ---------------------------------------------------------------------------
# Access-control decorator
# ---------------------------------------------------------------------------

def staff_required(view_func):
    """Require login AND is_staff=True. Redirect non-staff to the order page."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, _('dashboard.error.no_permission'))
            return redirect('order')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _association_stats():
    """Return per-association statistics used by home and associations pages."""
    stats = []
    for assoc in Association.objects.order_by('name'):
        perfs = Performance.objects.filter(association=assoc)
        total_capacity = sum(p.max_tickets for p in perfs)
        tickets_sold = sum(p.tickets_sold() for p in perfs)
        t1_rev = sum(
            p.ticket1.price
            for p in Purchase.objects.filter(ticket1__association=assoc).select_related('ticket1')
        )
        t2_rev = sum(
            p.ticket2.price
            for p in Purchase.objects.filter(ticket2__association=assoc).select_related('ticket2')
        )
        stats.append({
            'association': assoc,
            'performance_count': perfs.count(),
            'total_capacity': total_capacity,
            'tickets_sold': tickets_sold,
            'tickets_left': total_capacity - tickets_sold,
            'revenue': t1_rev + t2_rev,
            'fill_pct': round(tickets_sold / total_capacity * 100) if total_capacity else 0,
        })
    return stats


# ---------------------------------------------------------------------------
# 1. Overview
# ---------------------------------------------------------------------------

@staff_required
def dashboard_home(request: HttpRequest) -> HttpResponse:
    total_purchases = Purchase.objects.count()
    total_revenue = sum(
        p.ticket1.price + p.ticket2.price
        for p in Purchase.objects.select_related('ticket1', 'ticket2')
    )
    total_capacity = sum(p.max_tickets for p in Performance.objects.all())
    total_tickets_sold = sum(p.tickets_sold() for p in Performance.objects.all())

    assoc_stats = _association_stats()

    performances = []
    for perf in Performance.objects.select_related('association').order_by('date'):
        sold = perf.tickets_sold()
        fill = round(sold / perf.max_tickets * 100) if perf.max_tickets else 0
        performances.append({
            'perf': perf,
            'sold': sold,
            'left': perf.tickets_left(),
            'fill_pct': fill,
            'warning': fill >= 80,
            'sold_out': fill >= 100,
        })

    recent_purchase_logs = PurchaseAuditLog.objects.select_related('user', 'purchase').order_by('-timestamp')[:10]
    recent_login_logs = LoginAuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    data_ready = all(a['association'].image for a in assoc_stats)

    return render(request, 'dashboard/home.html', {
        'total_purchases': total_purchases,
        'total_revenue': total_revenue,
        'total_capacity': total_capacity,
        'total_tickets_sold': total_tickets_sold,
        'assoc_stats': assoc_stats,
        'performances': performances,
        'recent_purchase_logs': recent_purchase_logs,
        'recent_login_logs': recent_login_logs,
        'data_ready': data_ready,
    })


# ---------------------------------------------------------------------------
# 2. Associations
# ---------------------------------------------------------------------------

@staff_required
def dashboard_associations(request: HttpRequest) -> HttpResponse:
    return render(request, 'dashboard/associations.html', {
        'assoc_stats': _association_stats(),
        'upload_form': LogoUploadForm(),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def dashboard_association_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = AssociationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            image = form.cleaned_data.get('image') or None
            if Association.objects.filter(name=name).exists():
                form.add_error('name', _('dashboard.associations.error.name_exists'))
            else:
                Association.objects.create(name=name, image=image)
                messages.success(request, _('dashboard.associations.created') % {'name': name})
                return redirect('dashboard:dashboard_associations')
    else:
        form = AssociationForm()
    return render(request, 'dashboard/association_form.html', {'form': form, 'action': 'Create'})


@staff_required
@require_http_methods(['GET', 'POST'])
def dashboard_association_edit(request: HttpRequest, name: str) -> HttpResponse:
    assoc = get_object_or_404(Association, name=name)
    if request.method == 'POST':
        form = AssociationForm(request.POST)
        if form.is_valid():
            new_name = form.cleaned_data['name']
            image = form.cleaned_data.get('image') or None
            if new_name != assoc.name and Association.objects.filter(name=new_name).exists():
                form.add_error('name', _('dashboard.associations.error.name_exists'))
            else:
                with transaction.atomic():
                    if new_name != assoc.name:
                        new_assoc = Association.objects.create(name=new_name, image=image)
                        Performance.objects.filter(association=assoc).update(association=new_assoc)
                        assoc.delete()
                    else:
                        assoc.image = image
                        assoc.save()
                messages.success(request, _('dashboard.associations.updated'))
                return redirect('dashboard:dashboard_associations')
    else:
        form = AssociationForm(initial={'name': assoc.name, 'image': assoc.image or ''})
    return render(request, 'dashboard/association_form.html', {
        'form': form, 'action': 'Edit', 'assoc': assoc,
    })


@staff_required
@require_POST
def dashboard_association_delete(request: HttpRequest, name: str) -> HttpResponse:
    assoc = get_object_or_404(Association, name=name)
    if Performance.objects.filter(association=assoc).exists():
        messages.error(request, _('dashboard.associations.error.has_performances') % {'name': name})
    else:
        assoc.delete()
        messages.success(request, _('dashboard.associations.deleted') % {'name': name})
    return redirect('dashboard:dashboard_associations')


@staff_required
@require_POST
def dashboard_logo_upload(request: HttpRequest) -> HttpResponse:
    form = LogoUploadForm(request.POST, request.FILES)
    if form.is_valid():
        logo = form.cleaned_data['logo']
        media_path = os.path.join(settings.BASE_DIR, 'iftf_duoverkoop', 'media', 'associations')
        os.makedirs(media_path, exist_ok=True)
        with open(os.path.join(media_path, logo.name), 'wb+') as fh:
            for chunk in logo.chunks():
                fh.write(chunk)
        messages.success(request, _('dashboard.associations.logo_uploaded') % {'name': logo.name})
    else:
        messages.error(request, _('dashboard.associations.error.invalid_logo'))
    return redirect('dashboard:dashboard_associations')


# ---------------------------------------------------------------------------
# 3. Performances
# ---------------------------------------------------------------------------

@staff_required
def dashboard_performances(request: HttpRequest) -> HttpResponse:
    performances = []
    for perf in Performance.objects.select_related('association').order_by('association__name', 'date'):
        sold = perf.tickets_sold()
        fill = round(sold / perf.max_tickets * 100) if perf.max_tickets else 0
        performances.append({
            'perf': perf,
            'sold': sold,
            'left': perf.tickets_left(),
            'fill_pct': fill,
            'warning': fill >= 80,
            'sold_out': fill >= 100,
        })
    return render(request, 'dashboard/performances.html', {'performances': performances})


@staff_required
@require_http_methods(['GET', 'POST'])
def dashboard_performance_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = PerformanceForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            Performance.objects.create(
                key=d['key'],
                name=d['name'],
                association=get_object_or_404(Association, name=d['association']),
                date=d['date'],
                price=d['price'],
                max_tickets=d['max_tickets'],
            )
            messages.success(request, _('dashboard.performances.created') % {'key': d['key']})
            return redirect('dashboard:dashboard_performances')
    else:
        form = PerformanceForm()
    return render(request, 'dashboard/performance_form.html', {'form': form, 'action': 'Create'})


@staff_required
@require_http_methods(['GET', 'POST'])
def dashboard_performance_edit(request: HttpRequest, key: str) -> HttpResponse:
    perf = get_object_or_404(Performance, key=key)
    sold = perf.tickets_sold()
    if request.method == 'POST':
        form = PerformanceForm(request.POST, editing_key=key)
        if form.is_valid():
            d = form.cleaned_data
            if d['max_tickets'] < sold:
                form.add_error('max_tickets', _('dashboard.performances.error.below_sold') % {'sold': sold})
            else:
                assoc = get_object_or_404(Association, name=d['association'])
                with transaction.atomic():
                    new_key = d['key']
                    if new_key != key:
                        new_perf = Performance.objects.create(
                            key=new_key, name=d['name'], association=assoc,
                            date=d['date'], price=d['price'], max_tickets=d['max_tickets'],
                        )
                        Purchase.objects.filter(ticket1=perf).update(ticket1=new_perf)
                        Purchase.objects.filter(ticket2=perf).update(ticket2=new_perf)
                        perf.delete()
                    else:
                        perf.name = d['name']
                        perf.association = assoc
                        perf.date = d['date']
                        perf.price = d['price']
                        perf.max_tickets = d['max_tickets']
                        perf.save()
                messages.success(request, _('dashboard.performances.updated'))
                return redirect('dashboard:dashboard_performances')
    else:
        form = PerformanceForm(initial={
            'key': perf.key, 'name': perf.name, 'association': perf.association.name,
            'date': perf.date.strftime('%Y-%m-%dT%H:%M'),
            'price': perf.price, 'max_tickets': perf.max_tickets,
        }, editing_key=key)
    return render(request, 'dashboard/performance_form.html', {
        'form': form, 'action': 'Edit', 'perf': perf, 'sold': sold,
    })


@staff_required
@require_POST
def dashboard_performance_delete(request: HttpRequest, key: str) -> HttpResponse:
    perf = get_object_or_404(Performance, key=key)
    sold = perf.tickets_sold()
    if sold > 0:
        messages.error(request, _('dashboard.performances.error.has_tickets') % {'key': key, 'sold': sold})
    else:
        perf.delete()
        messages.success(request, _('dashboard.performances.deleted') % {'key': key})
    return redirect('dashboard:dashboard_performances')


# ---------------------------------------------------------------------------
# 4. Users
# ---------------------------------------------------------------------------

@staff_required
def dashboard_users(request: HttpRequest) -> HttpResponse:
    user_data = [
        {
            'user': u,
            'group': u.groups.first().name if u.groups.first() else '—',
            'purchases_created': u.purchases_created.count(),
        }
        for u in User.objects.prefetch_related('groups').order_by('username')
    ]
    return render(request, 'dashboard/users.html', {'user_data': user_data})


@staff_required
@require_http_methods(['GET', 'POST'])
def dashboard_user_create(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            user = User.objects.create_user(
                username=d['username'], email=d.get('email', ''),
                password=d['password'], is_staff=d.get('is_staff', False),
            )
            if d.get('group'):
                try:
                    user.groups.set([Group.objects.get(name=d['group'])])
                except Group.DoesNotExist:
                    pass
            messages.success(request, _('dashboard.users.created') % {'username': user.username})
            return redirect('dashboard:dashboard_users')
    else:
        form = CreateUserForm()
    return render(request, 'dashboard/user_form.html', {'form': form, 'action': 'Create'})


@staff_required
@require_http_methods(['GET', 'POST'])
def dashboard_user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = EditUserForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            target.email = d.get('email', '')
            target.is_staff = d.get('is_staff', False)
            target.is_active = d.get('is_active', True)
            if d.get('new_password'):
                target.set_password(d['new_password'])
            target.save()
            target.groups.clear()
            if d.get('group'):
                try:
                    target.groups.add(Group.objects.get(name=d['group']))
                except Group.DoesNotExist:
                    pass
            messages.success(request, _('dashboard.users.updated') % {'username': target.username})
            return redirect('dashboard:dashboard_users')
    else:
        current_group = target.groups.first()
        form = EditUserForm(initial={
            'email': target.email, 'is_staff': target.is_staff,
            'is_active': target.is_active,
            'group': current_group.name if current_group else '',
        })
    return render(request, 'dashboard/user_form.html', {'form': form, 'action': 'Edit', 'target': target})


@staff_required
@require_POST
def dashboard_user_delete(request: HttpRequest, user_id: int) -> HttpResponse:
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, _('dashboard.users.error.cannot_delete_self'))
    elif target.purchases_created.exists() or target.purchases_modified.exists():
        messages.error(request, _('dashboard.users.error.has_purchases') % {'username': target.username})
    else:
        username = target.username
        target.delete()
        messages.success(request, _('dashboard.users.deleted') % {'username': username})
    return redirect('dashboard:dashboard_users')


# ---------------------------------------------------------------------------
# 5. Audit log
# ---------------------------------------------------------------------------

@staff_required
def dashboard_audit(request: HttpRequest) -> HttpResponse:
    qs = PurchaseAuditLog.objects.select_related('user', 'purchase').order_by('-timestamp')
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    purchase_filter = request.GET.get('purchase', '')
    if action_filter:
        qs = qs.filter(action=action_filter)
    if user_filter:
        qs = qs.filter(user__username__icontains=user_filter)
    if purchase_filter:
        qs = qs.filter(purchase__id=purchase_filter)

    page = Paginator(qs, 50).get_page(request.GET.get('page'))

    lqs = LoginAuditLog.objects.select_related('user').order_by('-timestamp')
    login_event_filter = request.GET.get('login_event', '')
    login_user_filter = request.GET.get('login_user', '')
    if login_event_filter:
        lqs = lqs.filter(event=login_event_filter)
    if login_user_filter:
        lqs = lqs.filter(username__icontains=login_user_filter)

    login_page = Paginator(lqs, 50).get_page(request.GET.get('login_page'))

    return render(request, 'dashboard/audit.html', {
        'page': page,
        'login_page': login_page,
        'users': User.objects.order_by('username'),
        'action_filter': action_filter,
        'user_filter': user_filter,
        'purchase_filter': purchase_filter,
        'login_event_filter': login_event_filter,
        'login_user_filter': login_user_filter,
    })


@staff_required
def dashboard_audit_detail(request: HttpRequest, log_id: int) -> HttpResponse:
    entry = get_object_or_404(PurchaseAuditLog, pk=log_id)
    return render(request, 'dashboard/audit_detail.html', {
        'entry': entry,
        'changes_pretty': json.dumps(entry.changes, indent=2) if entry.changes else None,
    })


# ---------------------------------------------------------------------------
# 6. System
# ---------------------------------------------------------------------------

@staff_required
def dashboard_system(request: HttpRequest) -> HttpResponse:
    from django.db import connection
    return render(request, 'dashboard/system.html', {
        'db_vendor': connection.vendor,
        'model_counts': {
            'Associations': Association.objects.count(),
            'Performances': Performance.objects.count(),
            'Purchases': Purchase.objects.count(),
            'Audit log entries': PurchaseAuditLog.objects.count(),
            'Login events': LoginAuditLog.objects.count(),
            'Users': User.objects.count(),
        },
        'send_emails': getattr(settings, 'SEND_EMAILS', False),
        'debug': settings.DEBUG,
    })


@staff_required
@require_POST
def dashboard_sync_permissions(request: HttpRequest) -> HttpResponse:
    try:
        setup_permission_groups()
        messages.success(request, _('dashboard.system.permissions_synced'))
    except Exception as e:
        messages.error(request, _('dashboard.system.permissions_sync_failed') % {'error': e})
    return redirect('dashboard:dashboard_system')

