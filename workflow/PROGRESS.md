# Progression JED

Mettre à jour ce fichier après la revue de chaque tâche. Une tâche n'est « terminée » qu'après validation de ses critères, relecture du diff et commit du porteur.

## État

- **Terminé** : workflow initial et intégration des décisions métier A2–A8 dans le registre et le document de conception ; JED-01 — socle Django et configuration; JED-05 — approvisionnements et coût moyen; JED-06 P0 — corrections traçables de stock; JED-07 — ventes et lignes historiques; JED-08 — annulations de vente et journal d'audit métier; JED-09 — dépenses catégorisées, corrections et annulations auditées.
- **Reporté** : JED-06 P1 — inventaire physique hebdomadaire, à réaliser après stabilisation des flux P0.
- **Prochaine tâche** : JED-10 — indicateurs et tableaux de bord essentiels.
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
| 2026-10-27 | JED-05 — approvisionnements et coût moyen (correctifs) | Service central validant auteur, activité/produit, type, quantité et coût; produit verrouillé pendant l'écriture transactionnelle; cas A4 et calcul pondéré couverts. 18 tests inventaire/permissions/ventes OK; `manage.py check`, `makemigrations --check --dry-run` et `git diff --check` OK. En attente de validation et commit du porteur. | À committer par le porteur |
| 2026-10-28 | JED-05 — validation finale | Validation du porteur reçue. Le service d'approvisionnement et les tests sont déjà présents dans l'historique Git; aucun commit supplémentaire requis. | `b7bd84f` |
| 2026-10-28 | JED-06 — corrections de stock (P0) | Motif non blanc imposé aussi par le service central; mouvements non modifiables/supprimables via admin; références produit/activité protégées contre suppression en cascade; champs de stock en lecture seule dans l'admin produit; lien de correction ajouté à l'historique. 16 tests inventory OK; `manage.py check`, `makemigrations --check --dry-run`, diagnostics et `git diff --check` OK. Inventaire physique hebdomadaire P1 non inclus. | Correctifs en attente de commit |
| 2026-10-28 | JED-06 — validation et commit P0 | JED-06 P0 validée; correctifs et migration de protection des mouvements commités. | `b4be97a` |
| 2026-10-28 | JED-07 — ventes et lignes historiques | Vente groupée produits/prestations, snapshots prix/coût, mouvements atomiques, permissions et correctifs d'intégrité/marge; 39 tests sales OK; checks Django, migrations et diff propres. | `afa3593`, correctifs `b8b4d38` |
| 2026-10-28 | JED-08 — annulations et audit métier | Annulation idempotente, motifs obligatoires, restauration du stock par correction atomique et journal consultable; validation ciblée: `python manage.py test apps/sales apps/inventory --verbosity=1` -> 50 tests OK. | `feat: trace les annulations de vente` |
| 2026-10-28 | JED-09 — dépenses catégorisées | Saisie par activité/catégorie; montants Decimal positifs; catégories gérées en admin; corrections avec motif et audit avant/après; annulations traçables; employés limités à leurs dépenses; 7 tests JED-09 OK, `manage.py check`, `makemigrations --check --dry-run` et `git diff --check` OK. | En attente de commit |

## À remplir à chaque passage

- Tâche active : JED-09 — dépenses catégorisées (validée)
- Agent/outils utilisés : — (assistant IA via Cline/KiloCode), Python 3.14.4, Django 6.1.2
- Changements et vérification : dépenses par activité/catégorie, correction avec motif et audit, annulation et périmètre d'accès employés; 7 tests OK; checks Django, migrations et diff propres
- Bloqueurs / décision attendue : aucun bloqueur connu
- Prochaine tâche débloquée : JED-10 — indicateurs et tableaux de bord essentiels
