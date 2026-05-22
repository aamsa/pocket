from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ledger.models import Household, HouseholdMember
from apps.transactions.models import Source


class Command(BaseCommand):
    help = "Create a household, attach the given users, and assign unowned sources to it."

    def add_arguments(self, parser):
        parser.add_argument("usernames", nargs="+", help="Usernames to attach to the household.")
        parser.add_argument("--name", default="Household", help="Household name.")

    def handle(self, *args, **options):
        User = get_user_model()
        household, created = Household.objects.get_or_create(name=options["name"])

        attached = []
        for username in options["usernames"]:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User '{username}' does not exist.")
            HouseholdMember.objects.get_or_create(user=user, defaults={"household": household})
            attached.append(username)

        # Sources seeded with household=None are claimed by the household so
        # both partners share one list.
        assigned = Source.objects.filter(household__isnull=True).update(household=household)

        verb = "Created" if created else "Using existing"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} household '{household.name}'. Members: {', '.join(attached)}. "
                f"Assigned {assigned} source(s)."
            )
        )
