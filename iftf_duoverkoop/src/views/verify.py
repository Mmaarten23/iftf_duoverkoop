"""
views/verify.py – Verification code lookup page.
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from iftf_duoverkoop.src.core.models import Purchase, Performance
from iftf_duoverkoop.src.core.auth import is_association_rep
from iftf_duoverkoop.src.core.verification_codes import validate_code_format, normalize_code


@login_required
@permission_required('iftf_duoverkoop.verify_purchase', raise_exception=True)
@require_http_methods(["GET", "POST"])
def verify_code(request: HttpRequest) -> HttpResponse:
    """
    Verification code lookup page (Support Staff + Association Representatives).

    For association representatives: requires selecting one of their own
    performances as an additional check. The code is only considered valid if
    it belongs to the selected performance.  Four distinct outcomes are shown:
      1. Code valid for the selected performance   → success
      2. Code valid for the association, but a different performance
      3. Code found but belongs to a different association entirely
      4. Code not known in the system at all
    """
    purchase = None
    error_message = None
    error_type = None   # 'wrong_performance' | 'wrong_association' | 'not_found'
    wrong_performances = []  # filled for case 2
    code = None
    is_rep = is_association_rep(request.user)

    # Fetch the rep's association and performances (empty for non-reps)
    rep_association = None
    rep_performances = []
    if is_rep:
        try:
            profile = request.user.association_rep_profile
            rep_association = profile.association
            rep_performances = list(
                Performance.objects.filter(association=rep_association).order_by('date')
            )
        except Exception:
            pass  # no profile set → behaves like a support-staff member

    selected_performance_key = None

    if request.method == 'POST':
        code = request.POST.get('verification_code', '').strip()
        selected_performance_key = request.POST.get('performance_key', '').strip() or None

        if not code:
            error_message = _('verify.error_empty')
        elif not validate_code_format(code):
            error_message = _('verify.error_invalid_format')
        else:
            normalized = normalize_code(code)
            try:
                found_purchase = Purchase.objects.select_related(
                    'ticket1__association', 'ticket2__association'
                ).get(verification_code=normalized)

                if is_rep and rep_association:
                    # Determine which (if any) tickets belong to this association
                    assoc_tickets = [
                        t for t in (found_purchase.ticket1, found_purchase.ticket2)
                        if t.association == rep_association
                    ]

                    if not assoc_tickets:
                        # The code exists but is not for this association at all
                        error_type = 'wrong_association'
                        error_message = _('verify.error_wrong_association')
                    elif selected_performance_key and any(
                        t.key == selected_performance_key for t in assoc_tickets
                    ):
                        # Code is valid for the selected performance ✓
                        purchase = found_purchase
                    else:
                        # Code belongs to this association, but a different performance
                        error_type = 'wrong_performance'
                        error_message = _('verify.error_wrong_performance')
                        wrong_performances = assoc_tickets
                else:
                    # Support staff / no rep profile → show full details as before
                    purchase = found_purchase

            except Purchase.DoesNotExist:
                error_type = 'not_found'
                error_message = _('verify.error_not_found')

    return render(request, 'verification/verify_code.html', {
        'purchase': purchase,
        'error_message': error_message,
        'error_type': error_type,
        'wrong_performances': wrong_performances,
        'code': code,
        'is_rep': is_rep,
        'rep_association': rep_association,
        'rep_performances': rep_performances,
        'selected_performance_key': selected_performance_key,
    })

