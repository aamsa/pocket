from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ledger.models import Household, HouseholdMember


class Command(BaseCommand):
    help = "Create a household, attach the given users, and make the first one the head."

    def add_arguments(self, parser):
        parser.add_argument("usernames", nargs="+", help="Usernames to attach (first becomes head).")
        parser.add_argument("--name", default="Household", help="Household name.")

    def handle(self, *args, **options):
        User = get_user_model()
        household, created = Household.objects.get_or_create(name=options["name"])

        attached = []
        first_user = None
        for username in options["usernames"]:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User '{username}' does not exist.")
            HouseholdMember.objects.get_or_create(user=user, defaults={"household": household})
            attached.append(username)
            if first_user is None:
                first_user = user

        # First listed user heads the family (unless one is already set).
        if household.head_id is None and first_user is not None:
            household.head = first_user
            household.save(update_fields=["head"])

        head_name = household.head.username if household.head_id else "—"
        verb = "Created" if created else "Using existing"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} household '{household.name}'. Members: {', '.join(attached)}. Head: {head_name}."
            )
        )
