import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reset a user's password and re-flag them for forced password change."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--password",
            help="Password (skip prompt). For non-interactive use only.",
        )
        parser.add_argument(
            "--no-force-change",
            action="store_true",
            help="Do not require the user to change their password on next login.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError(f"User '{options['username']}' not found.") from exc

        password = options.get("password") or self._prompt_password()
        user.set_password(password)
        user.save(update_fields=["password"])

        profile = user.profile
        profile.force_password_change = not options["no_force_change"]
        profile.save(update_fields=["force_password_change"])

        self.stdout.write(self.style.SUCCESS(
            f"Password reset for '{user.username}'."
        ))

    def _prompt_password(self):
        while True:
            p1 = getpass.getpass("New password: ")
            if len(p1) < 8:
                self.stdout.write(self.style.ERROR("Password must be at least 8 characters."))
                continue
            p2 = getpass.getpass("New password (again): ")
            if p1 != p2:
                self.stdout.write(self.style.ERROR("Passwords don't match."))
                continue
            return p1
