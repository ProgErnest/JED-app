"""Configuration de l'application ``inventory`` (JED-05)."""

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"
    verbose_name = "Mouvements de stock"
