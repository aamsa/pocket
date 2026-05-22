"""One-time importer: legacy pocket model -> new income/expense ledger.

Reads a Django `dumpdata` JSON produced by the OLD code (the pocket/transfer
era) and rebuilds the data in the new model on a fresh database:

  auth.user              -> User (password hash preserved, so logins keep working)
  accounts.userprofile   -> UserProfile.display_name / force_password_change
  pockets.pocket         -> Source (flat tag); the tree is flattened, deduped by name
  transactions.category  -> Category (defaults mapped by name+kind; customs recreated)
  transactions.transaction -> Transaction (owner=created_by, source=its pocket)
  transactions.transfer  -> DROPPED (neither income nor expense; nets to zero)

Net worth is preserved at the household level: every rupiah traces to an
income/expense and transfers cancel, so starting balances stay 0 and
`Σincome − Σexpense` reproduces the real total.

Usage:
    python manage.py import_legacy path/to/legacy.json [--force]
"""

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from django.utils.dateparse import parse_datetime

from apps.ledger.models import Household, HouseholdMember
from apps.ledger.services import current_balance, household_balance
from apps.transactions.models import (
    CATEGORY_COLOR_CHOICES,
    SOURCE_ICON_CHOICES,
    Category,
    Source,
    Transaction,
)


VALID_SOURCE_ICONS = {value for value, _ in SOURCE_ICON_CHOICES}
VALID_COLORS = {value for value, _ in CATEGORY_COLOR_CHOICES}


class Command(BaseCommand):
    help = "Import legacy pocket-era dumpdata JSON into the new ledger model (run once on a fresh DB)."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the legacy dumpdata JSON.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Import even if transactions already exist (otherwise aborts).",
        )

    def handle(self, *args, **options):
        if Transaction.objects.exists() and not options["force"]:
            raise CommandError(
                "Transactions already exist. This command is meant for a fresh DB. "
                "Re-run with --force only if you know what you're doing."
            )

        try:
            with open(options["path"], encoding="utf-8") as fh:
                records = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read JSON: {exc}")

        # Group dumpdata records by model label.
        by_model = defaultdict(list)
        for rec in records:
            by_model[rec["model"].lower()].append(rec)

        users_raw = by_model.get("auth.user", [])
        profiles_raw = by_model.get("accounts.userprofile", [])
        pockets_raw = by_model.get("pockets.pocket", [])
        categories_raw = by_model.get("transactions.category", [])
        transactions_raw = by_model.get("transactions.transaction", [])
        transfers_raw = by_model.get("transactions.transfer", [])

        if not transactions_raw:
            self.stdout.write(self.style.WARNING("No transactions found in the dump."))

        with db_transaction.atomic():
            user_map = self._import_users(users_raw, profiles_raw)
            household = self._make_household(user_map)
            source_map = self._import_sources(pockets_raw, transactions_raw, household)
            category_map = self._import_categories(categories_raw, user_map)
            n_txn = self._import_transactions(
                transactions_raw, user_map, category_map, source_map
            )

        self._report(user_map, n_txn, len(source_map), len(category_map), len(transfers_raw))

    # ------------------------------------------------------------------ users

    def _import_users(self, users_raw, profiles_raw):
        User = get_user_model()
        user_map = {}
        for rec in users_raw:
            f = rec["fields"]
            user, _ = User.objects.update_or_create(
                username=f["username"],
                defaults={
                    "is_superuser": f.get("is_superuser", False),
                    "is_staff": f.get("is_staff", False),
                    "is_active": f.get("is_active", True),
                    "email": f.get("email", ""),
                    "first_name": f.get("first_name", ""),
                    "last_name": f.get("last_name", ""),
                },
            )
            # Preserve the password hash verbatim so existing logins keep working.
            if f.get("password"):
                user.password = f["password"]
            user.save()
            user_map[rec["pk"]] = user

        # Profiles: carry display name + force-password-change flag.
        prof_by_user_pk = {p["fields"]["user"]: p["fields"] for p in profiles_raw}
        for old_pk, user in user_map.items():
            pf = prof_by_user_pk.get(old_pk)
            profile = user.profile  # auto-created by the accounts signal
            if pf:
                profile.display_name = pf.get("display_name", "") or ""
                profile.force_password_change = pf.get("force_password_change", False)
            profile.starting_balance = 0
            profile.starting_balance_as_of = None
            profile.save()
        return user_map

    # -------------------------------------------------------------- household

    def _make_household(self, user_map):
        household, _ = Household.objects.get_or_create(name="Household")
        for user in user_map.values():
            HouseholdMember.objects.get_or_create(
                user=user, defaults={"household": household}
            )
        return household

    # ---------------------------------------------------------------- sources

    def _import_sources(self, pockets_raw, transactions_raw, household):
        """Map each pocket that owns >=1 transaction to a Source (deduped by
        name, reusing seeded sources). Returns old_pocket_pk -> Source."""
        used_pocket_pks = {t["fields"]["pocket"] for t in transactions_raw}

        # Seed reuse: claim seeded (household=None) sources by name.
        sources_by_name = {}
        for src in Source.objects.all():
            sources_by_name[src.name] = src

        source_map = {}
        for rec in pockets_raw:
            if rec["pk"] not in used_pocket_pks:
                continue
            f = rec["fields"]
            name = f["name"]
            src = sources_by_name.get(name)
            if src is None:
                icon = f.get("icon") if f.get("icon") in VALID_SOURCE_ICONS else "wallet"
                color = f.get("color_token") if f.get("color_token") in VALID_COLORS else "brand-500"
                src = Source(name=name, icon=icon, color_token=color)
                sources_by_name[name] = src
            # Claim for the household; carry archived state from the pocket.
            src.household = household
            if f.get("archived_at"):
                src.archived_at = parse_datetime(f["archived_at"])
            src.save()
            source_map[rec["pk"]] = src

        # Remove any seeded sources that were never claimed (still household-less).
        Source.objects.filter(household__isnull=True).delete()
        return source_map

    # ------------------------------------------------------------- categories

    def _import_categories(self, categories_raw, user_map):
        defaults_by_key = {
            (c.name, c.kind): c for c in Category.objects.filter(is_default=True)
        }
        category_map = {}
        for rec in categories_raw:
            f = rec["fields"]
            key = (f["name"], f["kind"])
            if f.get("is_default"):
                cat = defaults_by_key.get(key)
                if cat is None:  # a default that isn't in the new seed — recreate it
                    cat = Category.objects.create(
                        name=f["name"], kind=f["kind"],
                        icon=f.get("icon", "ellipsis"),
                        color_token=f.get("color_token", "brand-400"),
                        is_default=True,
                    )
                    defaults_by_key[key] = cat
            else:
                cat = Category.objects.create(
                    name=f["name"], kind=f["kind"],
                    icon=f.get("icon", "ellipsis"),
                    color_token=f.get("color_token", "brand-400"),
                    created_by=user_map.get(f.get("created_by")),
                    is_default=False,
                    archived_at=parse_datetime(f["archived_at"]) if f.get("archived_at") else None,
                )
            category_map[rec["pk"]] = cat
        return category_map

    # ----------------------------------------------------------- transactions

    def _import_transactions(self, transactions_raw, user_map, category_map, source_map):
        objs = []
        for rec in transactions_raw:
            f = rec["fields"]
            owner = user_map.get(f["created_by"])
            category = category_map.get(f["category"])
            if owner is None or category is None:
                raise CommandError(
                    f"Transaction {rec['pk']} references a missing user/category "
                    f"(created_by={f['created_by']}, category={f['category']})."
                )
            objs.append(
                Transaction(
                    kind=f["kind"],
                    amount=Decimal(str(f["amount"])),
                    category=category,
                    source=source_map.get(f["pocket"]),
                    occurred_on=date.fromisoformat(f["occurred_on"]),
                    notes=f.get("notes", "") or "",
                    owner=owner,
                )
            )
        Transaction.objects.bulk_create(objs)
        return len(objs)

    # --------------------------------------------------------------- reporting

    def _report(self, user_map, n_txn, n_sources, n_categories, n_transfers):
        self.stdout.write(self.style.SUCCESS("\nImport complete:"))
        self.stdout.write(f"  users:        {len(user_map)}")
        self.stdout.write(f"  sources:      {n_sources}")
        self.stdout.write(f"  categories:   {n_categories} (incl. mapped defaults)")
        self.stdout.write(f"  transactions: {n_txn}")
        self.stdout.write(f"  transfers:    {n_transfers} (dropped — not income/expense)")
        self.stdout.write("\nBalances (start=0; should match prod's current dashboard):")
        any_user = None
        for user in user_map.values():
            any_user = user
            bal = current_balance(user)
            self.stdout.write(f"  {user.username:<16} {bal:>16,.0f}".replace(",", "."))
        if any_user is not None:
            total = household_balance(any_user)
            self.stdout.write(self.style.SUCCESS(f"  {'HOUSEHOLD':<16} {total:>16,.0f}".replace(",", ".")))
