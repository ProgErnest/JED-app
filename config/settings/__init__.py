"""
Settings package — Django JED.

Par défaut, le module de configuration utilisé est `dev`.
Pour produire, définir la variable d'environnement ``DJANGO_SETTINGS_MODULE`` à
``config.settings.prod``.
"""
from .dev import *  # noqa: F401,F403
