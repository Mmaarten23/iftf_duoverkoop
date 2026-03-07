"""
views/verify.py – Verification code lookup page.
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from iftf_duoverkoop.src.core.models import Purchase
from iftf_duoverkoop.src.core.verification_codes import validate_code_format, normalize_code


@login_required
@permission_required('iftf_duoverkoop.verify_purchase', raise_exception=True)
@require_http_methods(["GET", "POST"])
def verify_code(request: HttpRequest) -> HttpResponse:
    """
    Verification code lookup page (Support Staff + Association Representatives).

    Allows authorised users to enter a three-word code and see purchase details.
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
            try:
                purchase = Purchase.objects.get(verification_code=normalize_code(code))
            except Purchase.DoesNotExist:
                error_message = _('verify.error_not_found')

    return render(request, 'verification/verify_code.html', {
        'purchase': purchase,
        'error_message': error_message,
        'code': code,
    })

