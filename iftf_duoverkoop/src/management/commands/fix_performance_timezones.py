"""Repair performance datetimes when they were imported/saved in the wrong timezone."""
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from iftf_duoverkoop.src.core.models import Performance


class Command(BaseCommand):
    help = (
        "Reinterpret stored Performance.date values from one timezone to another. "
        "Useful when datetimes were entered as local Brussels times but saved as UTC."
    )

    def add_arguments(self, parser):
        parser.add_argument('--from-tz', default='UTC', help='Timezone currently assumed by stored values (default: UTC).')
        parser.add_argument('--to-tz', default='Europe/Brussels', help='Timezone that should represent the intended wall time (default: Europe/Brussels).')
        parser.add_argument('--apply', action='store_true', help='Apply changes. Without this flag, the command runs in dry-run mode.')

    def handle(self, *args, **options):
        from_tz = ZoneInfo(options['from_tz'])
        to_tz = ZoneInfo(options['to_tz'])
        apply_changes = options['apply']

        performances = list(Performance.objects.all().order_by('date'))
        if not performances:
            self.stdout.write(self.style.WARNING('No performances found.'))
            return

        self.stdout.write(f'Found {len(performances)} performances.')
        self.stdout.write(f'Reinterpreting wall time from {from_tz.key} to {to_tz.key}.')

        updates = []
        for perf in performances:
            current = perf.date
            if timezone.is_naive(current):
                current = timezone.make_aware(current, from_tz)
            current_in_from = current.astimezone(from_tz)
            naive_wall = current_in_from.replace(tzinfo=None)
            corrected = timezone.make_aware(naive_wall, to_tz)

            updates.append((perf, corrected))
            self.stdout.write(
                f"- {perf.key}: {perf.date.isoformat()} -> {corrected.isoformat()}"
            )

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry-run complete. Re-run with --apply to save changes.'))
            return

        with transaction.atomic():
            for perf, corrected in updates:
                perf.date = corrected
                perf.save(update_fields=['date'])

        self.stdout.write(self.style.SUCCESS(f'Updated {len(updates)} performances.'))

