from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=80, blank=True)
    force_password_change = models.BooleanField(default=True)
    # One starting figure per person — the total money they have "as of"
    # `starting_balance_as_of`. Current balance runs forward from here with
    # income/expense. Correctable anytime.
    starting_balance = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    starting_balance_as_of = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def label(self):
        return self.display_name or self.user.username
