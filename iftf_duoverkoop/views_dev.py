from datetime import datetime

from django.shortcuts import redirect
from django.urls import reverse

from iftf_duoverkoop.src import db


def load_db(request):
    db.create_association('Wina', 'associations/wina.jpg')
    db.create_association('Politika', 'associations/politika.png')
    db.create_performance(
        key="Wina1104",
        date=datetime(2022, 4, 11),
        association=db.get_association('Wina'),
        name="Van je familie moet je het maar hebben",
        price=5,
        tickets=30
    )
    db.create_performance(
        key="Politika0104",
        date=datetime(2022, 4, 1),
        association=db.get_association('Politika'),
        name="Working title",
        price=5,
        tickets=30
    )
    db.create_performance(
        key="Politika0304",
        date=datetime(2022, 4, 3),
        association=db.get_association('Politika'),
        name="Working title",
        price=5,
        tickets=30
    )
    db.create_performance(
        key="Politika0504",
        date=datetime(2022, 4, 5),
        association=db.get_association('Politika'),
        name="Working title",
        price=5,
        tickets=30
    )
    return redirect(reverse('order'))
