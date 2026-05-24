import uuid

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q


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
# Transactions — the whole core. Income or expense, owned by a person,
# tagged with a category.
# ---------------------------------------------------------------------------

TXN_KIND_INCOME = "income"
TXN_KIND_EXPENSE = "expense"
TXN_KIND_CHOICES = [
    (TXN_KIND_INCOME, "Income"),
    (TXN_KIND_EXPENSE, "Expense"),
]


class TransactionQuerySet(models.QuerySet):
    def for_user(self, user):
        """Transactions owned by a single user."""
        return self.filter(owner=user)

    def for_household(self, user):
        """Transactions owned by anyone in the user's household."""
        from apps.ledger.services import household_user_ids

        return self.filter(owner_id__in=household_user_ids(user))

    def in_period(self, start, end):
        qs = self
        if start:
            qs = qs.filter(occurred_on__gte=start)
        if end:
            qs = qs.filter(occurred_on__lte=end)
        return qs


class LiveTransactionManager(models.Manager.from_queryset(TransactionQuerySet)):
    """Default manager: excludes soft-deleted (archived) transactions, so they
    disappear from every list/sum/chart app-wide without touching each query."""

    def get_queryset(self):
        return super().get_queryset().filter(archived_at__isnull=True)


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=8, choices=TXN_KIND_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="transactions")
    occurred_on = models.DateField()
    notes = models.CharField(max_length=500, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    recurring_rule = models.ForeignKey(
        "ledger.RecurringRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Soft delete: archived rows are hidden from the default `objects` manager
    # (so they vanish from lists/sums/charts), but stay restorable via Undo.
    archived_at = models.DateTimeField(null=True, blank=True)

    objects = LiveTransactionManager()                # live rows only — app-wide default
    all_objects = TransactionQuerySet.as_manager()    # includes archived (restore)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [
            models.Index(fields=["owner", "-occurred_on"]),
            models.Index(fields=["category", "-occurred_on"]),
        ]
        constraints = [
            CheckConstraint(condition=Q(amount__gt=0), name="txn_amount_positive"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount} ({self.occurred_on})"

    @property
    def signed_amount(self):
        return self.amount if self.kind == TXN_KIND_INCOME else -self.amount
