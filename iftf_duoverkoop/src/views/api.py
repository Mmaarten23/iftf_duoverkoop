"""
views/api.py – Internal JSON API endpoints consumed by the front-end JS.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse

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
    """Return a {key: price} map for all performances that still have tickets."""
    try:
        return JsonResponse({'prices': {
            p.key: float(p.price)
            for p in db.get_all_performances()
            if p.tickets_left() > 0
        }})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

