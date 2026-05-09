import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Create a new user account. Only the superuser should run this. "
        "The new user will be required to change their password on first login."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--superuser", action="store_true")
        parser.add_argument("--display-name", default="")
        parser.add_argument(
            "--password",
            help="Password (skip prompt). For non-interactive use only.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists.")

        password = options.get("password") or self._prompt_password()

        user = User.objects.create_user(
            username=username,
            password=password,
            is_staff=options["superuser"],
            is_superuser=options["superuser"],
        )

        # The post_save signal creates UserProfile.
        profile = user.profile
        profile.display_name = options["display_name"] or username
        profile.force_password_change = True
        profile.save()

        kind = "Superuser" if options["superuser"] else "User"
        self.stdout.write(self.style.SUCCESS(
            f"{kind} '{username}' created. Forced password change on first login."
        ))

    def _prompt_password(self):
        while True:
            p1 = getpass.getpass("Password: ")
            if len(p1) < 8:
                self.stdout.write(self.style.ERROR("Password must be at least 8 characters."))
                continue
            p2 = getpass.getpass("Password (again): ")
            if p1 != p2:
                self.stdout.write(self.style.ERROR("Passwords don't match."))
                continue
            return p1
