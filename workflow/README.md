# Workflow de développement JED

Ce dossier transforme [JED_conception_V3.md](../JED_conception_V3.md) en une méthode de travail utilisable avec Cline, Kilo Code et, ponctuellement, GitHub Copilot gratuit. Le dépôt ne contient pas encore de code : le premier résultat attendu est un socle Django minimal, puis des parcours métier livrés par petits lots.

## Mode d'emploi

1. Le porteur du projet choisit la prochaine tâche **débloquée** dans [PLAN.md](PLAN.md).
2. Il copie le prompt de [AGENT_GUIDE.md](AGENT_GUIDE.md) dans l'outil choisi, en remplaçant les champs entre crochets par l'ID et le titre de la tâche. Il joint ou fait lire la fiche de la tâche dans `PLAN.md` et `JED_conception_V3.md`.
3. L'agent inspecte le dépôt, résume le périmètre et les fichiers prévus, puis réalise cette tâche seulement. Pour un point métier non tranché, il s'arrête sur ce point, décrit les options et continue les parties indépendantes.
4. L'agent vérifie les critères de la fiche, présente les changements et les limites. Le porteur relit le diff et lance les vérifications manuelles indiquées.
5. Après validation, le porteur crée le commit proposé et met à jour [PROGRESS.md](PROGRESS.md). Une seule tâche active à la fois au début du projet.

## Quel outil pour quelle tâche

- **Cline ou Kilo Code** : outil principal pour une tâche verticale (modèles + logique serveur + vues/templates nécessaires). Donner une tâche courte et isolée, et vérifier le diff avant d'accepter.
- **GitHub Copilot gratuit** : aide ponctuelle pour expliquer un fichier, proposer une petite fonction ou relire un changement. Ne pas lui donner une deuxième tâche qui modifie les mêmes fichiers pendant qu'un autre agent travaille.
- **Front-end design d'Anthropic** : réserver aux écrans/templates et à leur présentation responsive. Les règles d'accès et calculs restent côté Django. Ne pas ajouter une nouvelle bibliothèque sans nécessité et justification.

Les noms d'interface peuvent évoluer; le workflow repose sur des prompts copiés manuellement et Git, sans service d'automatisation.

## Règles de découpage

- Une tâche = un résultat vérifiable, généralement réalisable en une session; éviter de confier toute une phase ou toute l'application à un agent.
- Les tâches séquentielles suivent les dépendances du plan. Deux agents ne travaillent en parallèle que sur des fichiers indépendants, dans des branches séparées, avec intégration et relecture manuelles.
- P0 passe avant P1/P2. Si le calendrier glisse, retirer les fonctions P1/P2; préserver permissions, cohérence des ventes/stock, historique, sauvegardes et restauration.
- Pas de suppression silencieuse d'une opération validée. Toute correction sensible conserve auteur, date et motif.
- Pas de nouvelle dépendance, refonte d'architecture, changement de base de données ou règle métier implicite sans la signaler et obtenir une décision du porteur.
- Pas de secrets ni de données réelles dans le dépôt, les prompts ou les captures.

## Fin de tâche

Une tâche est prête à relire quand ses critères d'acceptation sont passés, le diff est limité à son périmètre et l'agent a donné : résumé, fichiers modifiés, vérifications réalisées/résultats, questions ou risques, et message de commit suggéré. Le porteur, pas l'agent, décide de valider et de committer.

Avant la mise en production, le porteur suit les scénarios de recette du document de conception, et vérifie en particulier la restauration réelle d'une sauvegarde. Une sauvegarde créée seule ne valide pas cette étape.
