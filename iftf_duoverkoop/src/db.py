from datetime import datetime

from django.core.exceptions import ValidationError

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


def create_association(name: str, image: str = None) -> Association:
    association, _ = Association.objects.get_or_create(name=name, defaults={
        'name': name,
        'image': image
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


def validate_purchase(first_name, last_name, performance1, performance2):
    if not first_name or not last_name:
        return False
    if not performance1 or not performance2:
        return False
    if performance1 == performance2:
        return False
    if get_performance(performance1).tickets_left() <= 0 or get_performance(performance2).tickets_left() <= 0:
        return False
    return True


def handle_purchase(first_name: str, last_name: str, performance1: str, performance2: str) -> None:
    if not validate_purchase(first_name, last_name, performance1, performance2):
        raise ValidationError('Invalid purchase')
    Purchase.objects.create(
        date=datetime.now(),
        name=f"{first_name} {last_name}",
        ticket1=get_performance(performance1),
        ticket2=get_performance(performance2)
    )


def data_ready():
    is_ready = True
    for association in get_all_associations():
        if not association.image:
            is_ready = False
    return is_ready
