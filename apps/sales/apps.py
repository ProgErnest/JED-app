"""Configuration de l'application ``sales`` (JED-07)."""

from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sales"
    verbose_name = "Caisse / Ventes"
