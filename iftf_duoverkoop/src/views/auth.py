"""
views/auth.py – Login and logout views.
"""
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from iftf_duoverkoop.src.core.auth import is_association_rep


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    Handle user login with custom login page.

    GET:  Display the login form.
    POST: Authenticate and redirect to the intended page.
    """
    if request.user.is_authenticated:
        return redirect('verify_code' if is_association_rep(request.user) else 'order')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '') or request.GET.get('next', '') or None
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, _('login.success') % {'username': user.username})
            if next_url:
                return redirect(next_url)
            return redirect('verify_code' if is_association_rep(user) else 'order')
        return render(request, 'login.html', {
            'error_message': _('login.error'),
            'next': next_url or '',
        })

    return render(request, 'login.html', {'next': request.GET.get('next', '')})


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user and redirect to the login page."""
    username = request.user.username
    auth_logout(request)
    messages.info(request, _('login.logout_success') % {'username': username})
    return redirect('login')

