# JED — Gestion des ventes, stocks et rentabilité

Application web Django pour suivre les ventes, stocks, dépenses et estimations
de rentabilité de trois activités : **Restaurant-bar**, **Coiffure** et
**Boutique** (Bafoussam, Cameroun).

> 📖 Voir le document de conception [`JED_conception_V3.md`](JED_conception_V3.md)
> et la méthode de travail dans [`workflow/`](workflow/).

---

## Prérequis

- Python ≥ 3.10
- `git`
- (Facultatif) Un hébergeur supportant Django + SQLite (PaaS, VPS ou serveur
  partagé Python).

---

## Installation locale (développement)

```bash
# 1. Cloner le dépôt
git clone <url-du-dépôt>
cd JED-app

# 2. Créer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate          # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
python manage.py migrate

# 5. (Facultatif) Créer un super-utilisateur
python manage.py createsuperuser

# 6. Lancer le serveur de développement
python manage.py runserver
```

Le serveur est accessible sur <http://127.0.0.1:8000> (DEBUG activé).

### Remarques de développement

- Les paramètres de développement sont dans `config/settings/dev.py`.
- Le SECRET_KEY de dev est codé en dur dans `base.py` — **ne jamais l'utiliser
  en production**.
- Les variables d'environnement peuvent être définies dans un fichier `.env`
  (modèle : `.env.example`, **jamais commité**).

---

## Configuration de production

1. Copier `.env.example` en `.env` et remplir les valeurs réelles :
   ```bash
   cp .env.example .env
   ```
2. Générer une clé secrète :
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. Déployer avec :
   ```bash
   DJANGO_SETTINGS_MODULE=config.settings.prod \
   gunicorn config.wsgi:application
   ```
4. Vérifier `DEBUG = False` et `ALLOWED_HOSTS` correctement définis.

Voir [`workflow/PLAN.md`](workflow/PLAN.md) (JED-12) pour la procédure de
sauvegarde et de recette complète.

---

## Structure du projet

```
JED-app/
├── config/              # Configuration Django (settings, urls, wsgi, asgi)
│   └── settings/
│       ├── base.py      # Paramètres communs
│       ├── dev.py       # Développement (DEBUG=True)
│       └── prod.py      # Production (DEBUG=False, secrets depuis .env)
├── apps/                # Applications métier (JED-02 à JED-10)
├── templates/           # Templates HTML globaux
├── static/              # Fichiers statiques (CSS, JS)
├── manage.py
├── requirements.txt
├── .env.example         # Modèle pour les variables d'environnement
├── .gitignore
└── workflow/            # Méthode de travail et suivi de tâches
```

---

## Licence

Projet interne — JED, Bafoussam.
