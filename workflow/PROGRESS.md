# Progression JED

Mettre à jour ce fichier après la revue de chaque tâche. Une tâche n'est « terminée » qu'après validation de ses critères, relecture du diff et commit du porteur.

## État

- **Terminé** : workflow initial et intégration des décisions métier A2–A8 dans le registre et le document de conception ; JED-01 — socle Django et configuration.
- **En cours** : aucun.
- **Prochaine tâche** : JED-02 — comptes, activités et appartenances.
- **Décisions en attente** : aucune parmi A2 à A8; voir [DECISIONS.md](DECISIONS.md).
- **Problèmes connus** : dépôt sans code initial; date cible du 3 novembre 2026 très serrée.

## Journal des tâches

| Date | Tâche | Résultat / vérification | Commit |
|---|---|---|---|
| 2026-10-26 | Workflow et décisions A2–A8 | Création des consignes d'agents, du plan et du journal; décisions intégrées à `DECISIONS.md` et `JED_conception_V3.md`. | À committer par le porteur |
| 2026-10-26 | JED-01 — socle Django et configuration | Git initialisé; venv + Django 6.1.2 installés; structure `config/` avec settings `base`/`dev`/`prod`; `.gitignore`, `requirements.txt`, `.env.example`, `README.md` créés; migrations initiales exécutées (12 migrations OK); serveur dev démarré et répond HTTP 200 (admin → 302). Aucun secret suivi par Git. | `chore: initialise le socle Django` |

## À remplir à chaque passage

- Tâche active : — (JED-01 terminée, JED-02 suivante)
- Agent/outils utilisés : — (assistant IA via Cline/KiloCode), Python 3.14.4, Django 6.1.2
- Changements et vérification : voir journal ci-dessus
- Bloqueurs / décision attendue : aucun pour JED-01
- Prochaine tâche débloquée : JED-02 — comptes, activités et appartenances
