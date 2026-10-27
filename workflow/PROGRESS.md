# Progression JED

Mettre à jour ce fichier après la revue de chaque tâche. Une tâche n'est « terminée » qu'après validation de ses critères, relecture du diff et commit du porteur.

## État

- **Terminé** : workflow initial et intégration des décisions métier A2–A8 dans le registre et le document de conception ; JED-01 — socle Django et configuration.
- **En cours** : JED-04 — historique des prix corrigé et testé; validation finale et commit du porteur en attente.
- **Prochaine tâche** : JED-05 — approvisionnements et coût moyen, après validation de JED-04.
- **Décisions en attente** : aucune parmi A2 à A8; voir [DECISIONS.md](DECISIONS.md).
- **Problèmes connus** : date cible du 3 novembre 2026 très serrée; les deux réserves de déploiement JED-01 (chargement du fichier `.env` et dépendance Gunicorn) restent à traiter.

## Journal des tâches

| Date | Tâche | Résultat / vérification | Commit |
|---|---|---|---|
| 2026-10-26 | Workflow et décisions A2–A8 | Création des consignes d'agents, du plan et du journal; décisions intégrées à `DECISIONS.md` et `JED_conception_V3.md`. | À committer par le porteur |
| 2026-10-26 | JED-01 — socle Django et configuration | Git initialisé; venv + Django 6.1.2 installés; structure `config/` avec settings `base`/`dev`/`prod`; `.gitignore`, `requirements.txt`, `.env.example`, `README.md` créés; migrations initiales exécutées (12 migrations OK); serveur dev démarré et répond HTTP 200 (admin → 302). Aucun secret suivi par Git. | `chore: initialise le socle Django` |
| 2026-10-27 | JED-02 — comptes, activités et appartenances (correctifs) | Contraintes de base ajoutées pour la cohérence rôle/activité et l'unicité de l'appartenance globale; migration `0002` créée; tests des contraintes et des trois activités initiales: 5 tests OK; `manage.py check` et `makemigrations --check --dry-run` OK. En attente de validation finale et commit du porteur. | À committer par le porteur |
| 2026-10-27 | JED-03 — autorisations et périmètre des données (correctifs) | Superutilisateur assimilé au rôle global dans les helpers; listes et détails de ventes et mouvements filtrés par auteur pour les employés, sans réduire la visibilité des responsables/globaux. 11 tests ciblés OK; checks Django, migrations et diff OK. Suite globale: 39/40, seul échec connu sur le format localisé du détail vente (`5.00` attendu, `5,00 €` rendu), hors périmètre JED-03. En attente de validation et commit du porteur. | À committer par le porteur |
| 2026-10-27 | JED-04 — historique des prix (correctifs) | Historique produit/service corrigé : une seule entrée initiale, nouvelle version uniquement si le prix persisté change; édition non tarifaire, mouvement de stock et `save(update_fields=...)` n’altèrent pas l'historique. 5 tests catalogue et 1 test de snapshot de vente OK; checks Django, migrations et diff OK. Migration `0003` appliquée localement, supprimant uniquement 6 doublons strictement identiques (57 lignes avant, 51 après); périodes historiques distinctes conservées. En attente de validation et commit du porteur. | À committer par le porteur |

## À remplir à chaque passage

- Tâche active : JED-04 — correctifs implémentés, validation finale du porteur en attente
- Agent/outils utilisés : — (assistant IA via Cline/KiloCode), Python 3.14.4, Django 6.1.2
- Changements et vérification : voir journal ci-dessus
- Bloqueurs / décision attendue : validation finale et commit des lots en attente par le porteur
- Prochaine tâche débloquée : JED-05 — approvisionnements et coût moyen, après validation de JED-04
