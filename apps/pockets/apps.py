from django.apps import AppConfig


class PocketsConfig(AppConfig):
    name = "apps.pockets"
    label = "pockets"
    verbose_name = "Pockets"

    def ready(self):
        from . import signals  # noqa: F401
