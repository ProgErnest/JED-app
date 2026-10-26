"""
Paramètres de développement — projet JED.

Utilisé par défaut via ``DJANGO_SETTINGS_MODULE=config.settings`` (qui importe ``dev``).

Caractéristiques :
- DEBUG activé
- ALLOWED_HOSTS élargi (localhost, 127.0.0.1)
- Emails en console
- Ces paramètres ne doivent JAMAIS être utilisés en production.
"""
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Sécurité réduite en développement
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Log des emails dans la console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
