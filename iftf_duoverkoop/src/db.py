from datetime import datetime

from iftf_duoverkoop.models import Performance, Purchase, Association


def create_performance(key: str, date: datetime, association: Association, name: str, price: float,
                       tickets: int) -> Performance:
    performance, _ = Performance.objects.get_or_create(key=key, defaults={
        'date': date,
        'association': association,
        'name': name,
        'price': price,
        'max_tickets': tickets
    })
    return performance


def get_performance(key: str) -> Performance:
    return Performance.objects.get(key=key)


def get_all_performances() -> list:
    return Performance.objects.all()


def get_keyed_performances() -> list:
    return [(performance.key, performance) for performance in get_all_performances()]


def get_readable_keyed_performances() -> list:
    return [(performance.key, performance.selection()) for performance in get_all_performances() if
            performance.tickets_left() > 0]


def get_performances_by_association() -> dict:
    result = {association: [] for association in get_all_associations()}
    for performance in get_all_performances():
        if performance.association not in result:
            result[performance.association] = []
        result[performance.association].append(performance)
    return result


def create_association(name: str) -> Association:
    association, _ = Association.objects.get_or_create(name=name, defaults={
        'name': name
    })
    return association


def get_association(name: str) -> Association:
    return Association.objects.get(name=name)


def get_all_associations():
    return Association.objects.all()


def get_all_purchases() -> list:
    return Purchase.objects.all()


def get_purchases_by_user(user: str) -> list:
    return Purchase.objects.filter(name=user)


def handle_purchase(first_name: str, last_name: str, performance1: str, performance2: str) -> None:
    Purchase.objects.create(
        date=datetime.now(),
        name=f"{first_name} {last_name}",
        ticket1=get_performance(performance1),
        ticket2=get_performance(performance2)
    )


def get_tickets_sold(key):
    return Purchase.objects.filter(ticket1__key=key).count() + Purchase.objects.filter(ticket2__key=key).count()


def _DEBUG_clear_db():
    Purchase.objects.all().delete()
    Performance.objects.all().delete()
    Association.objects.all().delete()
