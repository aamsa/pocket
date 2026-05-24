import uuid

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q

from apps.transactions.models import TXN_KIND_CHOICES


# ---------------------------------------------------------------------------
# Household — a small grouping so a combined view can sum both partners.
# Replaces the old PocketShare invite/accept machinery: a user belongs to
# exactly one household (OneToOne), seeded once for this private app.
# ---------------------------------------------------------------------------


class Household(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60, default="Household")
    # The member who may manage the family (add/remove members, rename). Nullable
    # so deleting the head's user doesn't cascade the household; backfilled to the
    # earliest member by migration 0004.
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_households",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class HouseholdMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="members"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="household_membership",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} → {self.household}"


# ---------------------------------------------------------------------------
# Budget — a monthly per-category limit, with a "pace" signal.
# ---------------------------------------------------------------------------


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets"
    )
    category = models.ForeignKey(
        "transactions.Category", on_delete=models.CASCADE, related_name="budgets"
    )
    month = models.DateField(help_text="Normalised to the first of the month.")
    limit_amount = models.DecimalField(max_digits=14, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-month", "category__name"]
        constraints = [
            CheckConstraint(condition=Q(limit_amount__gt=0), name="budget_limit_positive"),
            models.UniqueConstraint(
                fields=["user", "category", "month"], name="budget_unique_user_category_month"
            ),
        ]

    def __str__(self):
        return f"{self.category} {self.month:%b %Y}: {self.limit_amount}"


# ---------------------------------------------------------------------------
# Goal — a savings target. Funding tracked as a single mutable current_amount
# (decoupled from the ledger; there are no accounts to move money between).
# ---------------------------------------------------------------------------


class Goal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals"
    )
    name = models.CharField(max_length=60)
    target_amount = models.DecimalField(max_digits=14, decimal_places=0)
    current_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    target_date = models.DateField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["archived_at", "target_date", "name"]
        constraints = [
            CheckConstraint(condition=Q(target_amount__gt=0), name="goal_target_positive"),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# RecurringRule — auto-creates income/expense entries on a cadence.
# Materialised by the run_recurring command.
# ---------------------------------------------------------------------------

CADENCE_WEEKLY = "weekly"
CADENCE_MONTHLY = "monthly"
CADENCE_CHOICES = [
    (CADENCE_WEEKLY, "Weekly"),
    (CADENCE_MONTHLY, "Monthly"),
]


class RecurringRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recurring_rules"
    )
    kind = models.CharField(max_length=8, choices=TXN_KIND_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    category = models.ForeignKey(
        "transactions.Category", on_delete=models.PROTECT, related_name="recurring_rules"
    )
    notes = models.CharField(max_length=500, blank=True)
    cadence = models.CharField(max_length=8, choices=CADENCE_CHOICES, default=CADENCE_MONTHLY)
    # weekly: 0–6 (Mon–Sun); monthly: 1–28 (clamped to month-end defensively).
    anchor_day = models.PositiveSmallIntegerField(default=1)
    next_run = models.DateField(db_index=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-active", "next_run"]
        constraints = [
            CheckConstraint(condition=Q(amount__gt=0), name="recurring_amount_positive"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount} ({self.get_cadence_display()})"
