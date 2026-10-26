"""
Paramètres communs (base) — projet JED.

Ce module contient les réglages partagés entre le développement et la production.
Les différences spécifiques à chaque environnement se trouvent dans ``dev.py``
et ``prod.py``.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --------------------------------------------------------------------------- #
# Sécurité
# --------------------------------------------------------------------------- #

# La clé secrète provient de la variable d'environnement en production.
# En développement, une valeur par défaut non secrète est utilisée.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-NE-PAS-UTILISER-EN-PROD",
)

# DEBUG et ALLOWED_HOSTS sont définis dans dev.py / prod.py
DEBUG = False
ALLOWED_HOSTS: list[str] = []


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tierce partie
    # Apps métier (ajoutées au fil des tâches JED-02 à JED-10)
    "apps.activities",
    "apps.accounts",
    "apps.catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# --------------------------------------------------------------------------- #
# Base de données — SQLite
# --------------------------------------------------------------------------- #

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# --------------------------------------------------------------------------- #
# Modèle utilisateur
# --------------------------------------------------------------------------- #

# JED-02 conserve le modèle ``User`` par défaut de Django et ajoute
# ``apps.accounts.ActivityMembership`` pour l'appartenance utilisateur → activité
# avec rôle (GLOBAL / MANAGER / EMPLOYEE). Aucun modèle utilisateur personnalisé
# n'est introduit ici pour ne pas casser les migrations ``auth`` déjà appliquées.
# AUTH_USER_MODEL n'est donc pas défini.


# --------------------------------------------------------------------------- #
# Validation des mots de passe
# --------------------------------------------------------------------------- #

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# --------------------------------------------------------------------------- #
# Internationalisation
# --------------------------------------------------------------------------- #

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------------- #
# Fichiers statiques et médias
# --------------------------------------------------------------------------- #

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# --------------------------------------------------------------------------- #
# Email
# --------------------------------------------------------------------------- #

# Par défaut, les emails sont affichés dans la console (développement).
# En production, configurer via les variables d'environnement.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "0") or "0")
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "False").lower() == "true"


# --------------------------------------------------------------------------- #
# Authentification
# --------------------------------------------------------------------------- #

LOGIN_REDIRECT_URL = "accounts:home"
LOGOUT_REDIRECT_URL = "accounts:login"


# --------------------------------------------------------------------------- #
# Autres
# --------------------------------------------------------------------------- #

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Messages framework — classes CSS personnalisées
from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}
