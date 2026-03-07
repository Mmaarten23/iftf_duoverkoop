"""
views/export.py – CSV export of all purchases grouped by association.
"""
import csv
from io import StringIO

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse

from iftf_duoverkoop.src import db


@login_required
@permission_required('iftf_duoverkoop.export_data', raise_exception=True)
def export(request: HttpRequest) -> HttpResponse:
    """Export all purchases to a CSV file, grouped by association (Support Staff only)."""
    time_format = "%d/%m/%Y %H:%M"

    file = StringIO()
    writer = csv.writer(file)
    writer.writerow([
        'Date of Purchase', 'Performance', 'Date of Performance',
        'Full Name', 'Email', 'Verification Code', 'Created By',
    ])

    all_purchases = db.get_all_purchases()
    for association in db.get_all_associations():
        writer.writerows([[''], [association.name]])
        for purchase in all_purchases:
            if purchase.ticket1.association == association:
                writer.writerow([
                    purchase.date.strftime(time_format), purchase.ticket1.name,
                    purchase.ticket1.date.strftime(time_format),
                    purchase.name, purchase.email,
                    purchase.verification_code, purchase.created_by.username,
                ])
            if purchase.ticket2.association == association:
                writer.writerow([
                    purchase.date.strftime(time_format), purchase.ticket2.name,
                    purchase.ticket2.date.strftime(time_format),
                    purchase.name, purchase.email,
                    purchase.verification_code, purchase.created_by.username,
                ])

    response = HttpResponse(file.getvalue(), content_type='application/csv')
    response['Content-Disposition'] = 'attachment; filename=export.csv'
    return response

