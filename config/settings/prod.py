"""
Paramètres de production — projet JED.

Utilisé en définissant ``DJANGO_SETTINGS_MODULE=config.settings.prod``.

Toutes les valeurs sensibles proviennent des variables d'environnement.
Aucun secret n'est codé en dur dans ce fichier.
"""
import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Les hôtes autorisés proviennent de la variable d'environnement
# DJANGO_ALLOWED_HOSTS, séparés par des virgules.
_allowed = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]

# --- Sécurité (HTTPS) ---
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --- Clé secrète ---
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # Obligatoire en production

# --- Base de données ---
# SQLite peut être utilisé, mais le chemin provient d'une variable d'environnement
# pour permettre un emplacement persistant sur l'hébergeur.
_db_path = os.environ.get("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _db_path,
    }
}

# --- Email ---
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "True").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "JED <noreply@jed-app.cm>")

# --- Logging de production ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "WARNING"),
        },
    },
}
