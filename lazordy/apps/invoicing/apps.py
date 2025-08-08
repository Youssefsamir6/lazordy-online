from django.apps import AppConfig


class InvoicingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invoicing'
    label = 'invoicing'

    def ready(self):
        from . import signals  # noqa: F401
