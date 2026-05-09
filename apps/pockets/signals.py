from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Pocket


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_main_pocket(sender, instance, created, **kwargs):
    """Every new user gets a 'Main' pocket — root of their pocket tree."""
    if not created:
        return
    Pocket.objects.get_or_create(
        owner=instance,
        is_main=True,
        defaults={
            "name": "Main",
            "icon": "wallet",
            "color_token": "brand-500",
            "parent": None,
        },
    )
