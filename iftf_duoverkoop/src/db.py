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
    # Get associations sorted alphabetically (they already are from get_all_associations)
    associations = get_all_associations()
    result = {association: [] for association in associations}
    for performance in get_all_performances():
        if performance.association in result:
            result[performance.association].append(performance)
    # Sort performances within each association by date
    for association in result:
        result[association].sort(key=lambda p: p.date)
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
    all_performances = [a for a in Association.objects.all()]
    all_performances.sort(key=lambda a: a.name.lower())
    return all_performances


def get_all_purchases() -> list[Purchase]:
    return Purchase.objects.all()


def get_purchases_by_user(user: str) -> list[Purchase]:
    return Purchase.objects.filter(name=user)


def validate_purchase(name, performance1, performance2):
    if not name:
        return False
    if not performance1 or not performance2:
        return False
    if performance1 == performance2:
        return False
    if get_performance(performance1).tickets_left() <= 0 or get_performance(performance2).tickets_left() <= 0:
        return False
    return True


def handle_purchase(name: str, email: str, performance1: str, performance2: str, created_by=None) -> Purchase:
    """
    Create a new purchase record with a unique verification code.

    Args:
        name: Customer name
        email: Customer email
        performance1: Key of first performance
        performance2: Key of second performance
        created_by: User creating the purchase (required for audit trail)

    Returns:
        Created Purchase instance with unique verification code

    Raises:
        ValidationError: If purchase validation fails
    """
    if not validate_purchase(name, performance1, performance2):
        raise ValidationError('Invalid purchase')

    # Import here to avoid circular dependency
    from iftf_duoverkoop.verification_codes import generate_unique_code

    # Get existing codes to ensure uniqueness
    existing_codes = set(Purchase.objects.values_list('verification_code', flat=True))

    # Generate unique verification code
    verification_code = generate_unique_code(existing_codes)

    purchase = Purchase.objects.create(
        date=datetime.now(),
        name=name,
        email=email,
        ticket1=get_performance(performance1),
        ticket2=get_performance(performance2),
        created_by=created_by,
        verification_code=verification_code
    )
    return purchase


def data_ready():
    is_ready = True
    for association in get_all_associations():
        if not association.image:
            is_ready = False
    return is_ready
