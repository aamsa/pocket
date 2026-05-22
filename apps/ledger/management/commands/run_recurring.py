from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.ledger.services import materialize_recurring


class Command(BaseCommand):
    help = "Materialise due recurring rules into Transactions, catching missed runs."

    def add_arguments(self, parser):
        parser.add_argument("--date", dest="as_of", help="Run as of a specific date (YYYY-MM-DD).")

    def handle(self, *args, **options):
        as_of = None
        if options.get("as_of"):
            try:
                as_of = date.fromisoformat(options["as_of"])
            except ValueError as exc:
                raise CommandError(f"Invalid --date: {exc}")
        count = materialize_recurring(as_of)
        self.stdout.write(
            self.style.SUCCESS(f"Created {count} transaction(s) as of {as_of or date.today()}.")
        )
