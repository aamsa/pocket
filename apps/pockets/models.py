import uuid

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q


POCKET_KIND_CASH = "cash"
POCKET_KIND_CREDIT = "credit"
POCKET_KIND_CHOICES = [
    (POCKET_KIND_CASH, "Cash"),
    (POCKET_KIND_CREDIT, "Credit card"),
]

POCKET_ICON_CHOICES = [
    ("wallet", "Wallet"),
    ("piggy-bank", "Piggy bank"),
    ("banknote", "Banknote"),
    ("credit-card", "Credit card"),
    ("landmark", "Bank"),
    ("coins", "Coins"),
    ("gem", "Gem"),
    ("shopping-bag", "Shopping"),
    ("home", "Home"),
    ("heart", "Heart"),
    ("plane", "Travel"),
    ("car", "Vehicle"),
    ("graduation-cap", "Education"),
    ("activity", "Health"),
]

POCKET_COLOR_CHOICES = [
    ("brand-200", "Sand"),
    ("brand-300", "Wheat"),
    ("brand-400", "Tan"),
    ("brand-500", "Caramel"),
    ("brand-600", "Toffee"),
    ("brand-700", "Mocha"),
]


class PocketQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)

    def archived(self):
        return self.filter(archived_at__isnull=False)

    def owned_by(self, user):
        return self.filter(owner=user)

    def cash(self):
        return self.filter(kind=POCKET_KIND_CASH)

    def credit(self):
        return self.filter(kind=POCKET_KIND_CREDIT)


class Pocket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pockets",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    is_main = models.BooleanField(default=False)
    kind = models.CharField(
        max_length=8, choices=POCKET_KIND_CHOICES, default=POCKET_KIND_CASH
    )
    statement_day = models.PositiveSmallIntegerField(null=True, blank=True)
    due_day = models.PositiveSmallIntegerField(null=True, blank=True)
    icon = models.CharField(max_length=40, default="wallet", choices=POCKET_ICON_CHOICES)
    color_token = models.CharField(
        max_length=20, default="brand-500", choices=POCKET_COLOR_CHOICES
    )
    notes = models.CharField(max_length=200, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PocketQuerySet.as_manager()

    class Meta:
        ordering = ["-is_main", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "parent", "name"],
                name="pocket_unique_name_within_parent",
            ),
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(is_main=True),
                name="pocket_one_main_per_owner",
            ),
            CheckConstraint(
                condition=(
                    Q(kind=POCKET_KIND_CASH, statement_day__isnull=True, due_day__isnull=True)
                    | Q(
                        kind=POCKET_KIND_CREDIT,
                        statement_day__gte=1,
                        statement_day__lte=28,
                        due_day__gte=1,
                        due_day__lte=28,
                    )
                ),
                name="pocket_credit_cycle_days",
            ),
            CheckConstraint(
                condition=Q(is_main=False) | Q(kind=POCKET_KIND_CASH),
                name="pocket_main_is_cash",
            ),
        ]

    def __str__(self):
        return self.name

    # Tree helpers --------------------------------------------------------

    def ancestors(self):
        """Yield ancestors from immediate parent up to root (excluding self)."""
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def descendants(self):
        """All descendants (any depth) in a single query (loaded into memory)."""
        all_for_owner = list(Pocket.objects.owned_by(self.owner).active())
        by_parent = {}
        for p in all_for_owner:
            by_parent.setdefault(p.parent_id, []).append(p)
        result = []

        def walk(parent_id):
            for child in by_parent.get(parent_id, []):
                result.append(child)
                walk(child.id)

        walk(self.id)
        return result

    def descendant_ids_with_self(self):
        return [self.id, *(d.id for d in self.descendants())]

    def ancestor_ids_with_self(self):
        return [self.id, *(a.id for a in self.ancestors())]


# ---------------------------------------------------------------------------
# Sharing
# ---------------------------------------------------------------------------

SHARE_PERMISSION_VIEW = "view"
SHARE_PERMISSION_MANAGE = "manage"
SHARE_PERMISSION_CHOICES = [
    (SHARE_PERMISSION_VIEW, "View only"),
    (SHARE_PERMISSION_MANAGE, "View and manage"),
]

SHARE_STATUS_PENDING = "pending"
SHARE_STATUS_ACCEPTED = "accepted"
SHARE_STATUS_DECLINED = "declined"
SHARE_STATUS_REVOKED = "revoked"
SHARE_STATUS_CHOICES = [
    (SHARE_STATUS_PENDING, "Pending"),
    (SHARE_STATUS_ACCEPTED, "Accepted"),
    (SHARE_STATUS_DECLINED, "Declined"),
    (SHARE_STATUS_REVOKED, "Revoked"),
]


class PocketShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pocket = models.ForeignKey(Pocket, on_delete=models.CASCADE, related_name="shares")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shares_sent",
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shares_received",
    )
    permission = models.CharField(max_length=10, choices=SHARE_PERMISSION_CHOICES)
    status = models.CharField(
        max_length=10, choices=SHARE_STATUS_CHOICES, default=SHARE_STATUS_PENDING
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-invited_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["pocket", "shared_with"],
                name="pocketshare_unique_pocket_user",
            ),
        ]

    def __str__(self):
        return f"{self.pocket.name} → {self.shared_with} ({self.permission}/{self.status})"
