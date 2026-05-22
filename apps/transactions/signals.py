from django.db.models.signals import post_migrate
from django.dispatch import receiver


DEFAULT_INCOME = [
    ("Salary", "briefcase", "brand-600"),
    ("Bonus", "gift", "brand-500"),
    ("Investment", "trending-up", "brand-700"),
    ("Refund", "rotate-cw", "brand-400"),
    ("Other Income", "sparkles", "brand-300"),
]

DEFAULT_EXPENSE = [
    ("Food", "utensils", "brand-500"),
    ("Groceries", "shopping-cart", "brand-600"),
    ("Transport", "car", "brand-700"),
    ("Utilities", "zap", "brand-400"),
    ("Rent/Mortgage", "home", "brand-700"),
    ("Health", "activity", "brand-500"),
    ("Entertainment", "popcorn", "brand-300"),
    ("Shopping", "shopping-bag", "brand-600"),
    ("Other Expense", "ellipsis", "brand-200"),
]

# Starter payment sources. Seeded with household=None; `seed_household`
# assigns them to the household so both partners share one list.
DEFAULT_SOURCES = [
    ("Cash", "banknote", "brand-500"),
    ("BCA", "landmark", "brand-700"),
    ("GoPay", "smartphone", "brand-400"),
    ("Card", "credit-card", "brand-600"),
    ("Other", "ellipsis", "brand-300"),
]


@receiver(post_migrate)
def seed_default_categories(sender, app_config, **kwargs):
    if app_config.label != "transactions":
        return
    from .models import (
        CATEGORY_KIND_EXPENSE,
        CATEGORY_KIND_INCOME,
        Category,
        Source,
    )

    if not Category.objects.filter(is_default=True).exists():
        rows = [
            Category(name=n, kind=CATEGORY_KIND_INCOME, icon=icon, color_token=color, is_default=True)
            for n, icon, color in DEFAULT_INCOME
        ] + [
            Category(name=n, kind=CATEGORY_KIND_EXPENSE, icon=icon, color_token=color, is_default=True)
            for n, icon, color in DEFAULT_EXPENSE
        ]
        Category.objects.bulk_create(rows)

    if not Source.objects.exists():
        Source.objects.bulk_create(
            [
                Source(name=n, icon=icon, color_token=color, household=None)
                for n, icon, color in DEFAULT_SOURCES
            ]
        )
