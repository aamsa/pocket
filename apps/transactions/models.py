import uuid

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, F, Q


CATEGORY_KIND_INCOME = "income"
CATEGORY_KIND_EXPENSE = "expense"
CATEGORY_KIND_CHOICES = [
    (CATEGORY_KIND_INCOME, "Income"),
    (CATEGORY_KIND_EXPENSE, "Expense"),
]

CATEGORY_ICON_CHOICES = [
    ("briefcase", "Briefcase"),
    ("trending-up", "Trending up"),
    ("gift", "Gift"),
    ("rotate-cw", "Refund"),
    ("sparkles", "Sparkles"),
    ("utensils", "Food"),
    ("shopping-cart", "Groceries"),
    ("car", "Transport"),
    ("zap", "Utilities"),
    ("home", "Home"),
    ("activity", "Health"),
    ("popcorn", "Entertainment"),
    ("shopping-bag", "Shopping"),
    ("ellipsis", "Other"),
]

CATEGORY_COLOR_CHOICES = [
    ("brand-200", "Sand"),
    ("brand-300", "Wheat"),
    ("brand-400", "Tan"),
    ("brand-500", "Caramel"),
    ("brand-600", "Toffee"),
    ("brand-700", "Mocha"),
]


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)

    def income(self):
        return self.filter(kind=CATEGORY_KIND_INCOME)

    def expense(self):
        return self.filter(kind=CATEGORY_KIND_EXPENSE)

    def for_user(self, user):
        return self.filter(Q(created_by=user) | Q(is_default=True))


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=40)
    kind = models.CharField(max_length=8, choices=CATEGORY_KIND_CHOICES)
    icon = models.CharField(max_length=40, default="ellipsis", choices=CATEGORY_ICON_CHOICES)
    color_token = models.CharField(max_length=20, default="brand-400", choices=CATEGORY_COLOR_CHOICES)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories",
    )
    is_default = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        ordering = ["kind", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "name", "kind"],
                name="category_unique_name_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

TXN_KIND_INCOME = "income"
TXN_KIND_EXPENSE = "expense"
TXN_KIND_CHOICES = [
    (TXN_KIND_INCOME, "Income"),
    (TXN_KIND_EXPENSE, "Expense"),
]


class TransactionQuerySet(models.QuerySet):
    def for_user(self, user):
        """Transactions in any pocket the user can view (owned or shared)."""
        from apps.pockets.permissions import visible_pocket_ids

        return self.filter(pocket_id__in=visible_pocket_ids(user))

    def in_period(self, start, end):
        qs = self
        if start:
            qs = qs.filter(occurred_on__gte=start)
        if end:
            qs = qs.filter(occurred_on__lte=end)
        return qs


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pocket = models.ForeignKey(
        "pockets.Pocket", on_delete=models.PROTECT, related_name="transactions"
    )
    kind = models.CharField(max_length=8, choices=TXN_KIND_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="transactions")
    occurred_on = models.DateField()
    notes = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transactions_created",
    )
    recurring_rule = models.ForeignKey(
        "RecurringRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TransactionQuerySet.as_manager()

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [
            models.Index(fields=["pocket", "-occurred_on"]),
            models.Index(fields=["category", "-occurred_on"]),
        ]
        constraints = [
            CheckConstraint(condition=Q(amount__gt=0), name="txn_amount_positive"),
        ]

    @property
    def signed_amount(self):
        return self.amount if self.kind == TXN_KIND_INCOME else -self.amount


# ---------------------------------------------------------------------------
# Transfers
# ---------------------------------------------------------------------------


class Transfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_pocket = models.ForeignKey(
        "pockets.Pocket", on_delete=models.PROTECT, related_name="transfers_out"
    )
    to_pocket = models.ForeignKey(
        "pockets.Pocket", on_delete=models.PROTECT, related_name="transfers_in"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    occurred_on = models.DateField()
    notes = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transfers_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [
            models.Index(fields=["from_pocket", "-occurred_on"]),
            models.Index(fields=["to_pocket", "-occurred_on"]),
        ]
        constraints = [
            CheckConstraint(condition=Q(amount__gt=0), name="transfer_amount_positive"),
            CheckConstraint(
                condition=~Q(from_pocket=F("to_pocket")),
                name="transfer_pockets_distinct",
            ),
        ]


# ---------------------------------------------------------------------------
# Recurring rules — schedule future Transactions on a fixed cadence
# ---------------------------------------------------------------------------

FREQUENCY_DAILY = "daily"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_YEARLY = "yearly"
FREQUENCY_CHOICES = [
    (FREQUENCY_DAILY, "Daily"),
    (FREQUENCY_WEEKLY, "Weekly"),
    (FREQUENCY_MONTHLY, "Monthly"),
    (FREQUENCY_YEARLY, "Yearly"),
]


class RecurringRule(models.Model):
    """A repeating income/expense schedule. Materialises into Transaction rows
    (one per occurrence) so reports, balances, and the projection dashboard
    can treat scheduled future entries as ordinary Transactions.

    Past-actual rows survive deletion of the rule (FK is SET_NULL on
    Transaction.recurring_rule)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=8, choices=TXN_KIND_CHOICES)
    pocket = models.ForeignKey(
        "pockets.Pocket", on_delete=models.PROTECT, related_name="recurring_rules"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="recurring_rules"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    notes = models.CharField(max_length=500, blank=True)

    frequency = models.CharField(max_length=8, choices=FREQUENCY_CHOICES)
    interval = models.PositiveSmallIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    occurrences = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recurring_rules_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-created_at"]
        indexes = [
            models.Index(fields=["pocket", "is_active"]),
            models.Index(fields=["created_by", "is_active"]),
        ]
        constraints = [
            CheckConstraint(condition=Q(amount__gt=0), name="recurring_amount_positive"),
            CheckConstraint(condition=Q(interval__gte=1), name="recurring_interval_min1"),
            CheckConstraint(
                condition=Q(end_date__isnull=False) | Q(occurrences__isnull=False),
                name="recurring_bounded",
            ),
        ]

    def cadence_label(self):
        """Human-friendly cadence summary — 'every month', 'every 2 weeks'."""
        unit = {
            FREQUENCY_DAILY: ("day", "days"),
            FREQUENCY_WEEKLY: ("week", "weeks"),
            FREQUENCY_MONTHLY: ("month", "months"),
            FREQUENCY_YEARLY: ("year", "years"),
        }[self.frequency]
        if self.interval == 1:
            return f"every {unit[0]}"
        return f"every {self.interval} {unit[1]}"
