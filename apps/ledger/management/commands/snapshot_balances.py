from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.ledger.services import write_snapshot


class Command(BaseCommand):
    help = "Write a daily balance snapshot per user (powers the net-worth trend). Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--date", dest="on_date", help="Backfill a specific date (YYYY-MM-DD).")

    def handle(self, *args, **options):
        on_date = None
        if options.get("on_date"):
            try:
                on_date = date.fromisoformat(options["on_date"])
            except ValueError as exc:
                raise CommandError(f"Invalid --date: {exc}")
        count = write_snapshot(on_date)
        self.stdout.write(
            self.style.SUCCESS(f"Snapshotted {count} user(s) for {on_date or date.today()}.")
        )
