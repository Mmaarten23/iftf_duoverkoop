"""
views/api.py – Internal JSON API endpoints consumed by the front-end JS.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from iftf_duoverkoop.src import db


@login_required
def db_info(request: HttpRequest) -> JsonResponse:
    """Return the database engine type (SQLite, PostgreSQL, …)."""
    from django.db import connection
    return JsonResponse({"database_type": connection.vendor})


@login_required
def get_performances_by_association(request: HttpRequest, association_name: str) -> JsonResponse:
    """Return all performances for a given association (used by filter dropdowns)."""
    try:
        association = db.get_association(association_name)
        performances = db.get_performances_by_association()[association]
        return JsonResponse({'performances': [
            {'key': p.key, 'name': p.selection()} for p in performances
        ]})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_performance_prices(request: HttpRequest) -> JsonResponse:
    """
    Return a {key: {price, discounted_price}} map for all performances.

    ``discounted_price`` is null when no discount is configured.
    Sold-out performances are excluded (the order form doesn't show them).
    """
    try:
        return JsonResponse({'prices': {
            p.key: {
                'price': float(p.price),
                'discounted_price': float(p.discounted_price) if p.discounted_price is not None else None,
            }
            for p in db.get_all_performances()
            if p.tickets_left() > 0
        }})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_availability(request: HttpRequest) -> JsonResponse:
    """
    Return current ticket availability for every performance.

    Consumed by the order-page polling loop to keep tile states fresh
    without a full page reload.  Returns ALL performances (including
    sold-out ones) so the client can detect transitions in both
    directions (available → sold-out and back).

    Response shape:
        {
            "performances": {
                "<key>": {
                    "tickets_left": <int>,
                    "max_tickets":  <int>
                },
                ...
            }
        }
    """
    try:
        performances = {
            p.key: {
                'tickets_left': p.tickets_left(),
                'max_tickets': p.max_tickets,
            }
            for p in db.get_all_performances()
        }
        return JsonResponse({'performances': performances})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

