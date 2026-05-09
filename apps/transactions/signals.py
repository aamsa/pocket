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


@receiver(post_migrate)
def seed_default_categories(sender, app_config, **kwargs):
    if app_config.label != "transactions":
        return
    from .models import (
        CATEGORY_KIND_EXPENSE,
        CATEGORY_KIND_INCOME,
        Category,
    )

    if Category.objects.filter(is_default=True).exists():
        return

    rows = [
        Category(name=n, kind=CATEGORY_KIND_INCOME, icon=icon, color_token=color, is_default=True)
        for n, icon, color in DEFAULT_INCOME
    ] + [
        Category(name=n, kind=CATEGORY_KIND_EXPENSE, icon=icon, color_token=color, is_default=True)
        for n, icon, color in DEFAULT_EXPENSE
    ]
    Category.objects.bulk_create(rows)
