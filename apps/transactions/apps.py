from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    name = "apps.transactions"
    label = "transactions"
    verbose_name = "Transactions"

    def ready(self):
        from . import signals  # noqa: F401
