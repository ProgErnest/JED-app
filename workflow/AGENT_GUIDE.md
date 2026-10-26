# Instructions communes aux agents

Copier ce prompt dans Cline, Kilo Code ou Copilot Chat et remplacer les champs entre crochets.

```text
Tu interviens sur JED, une application web Django pour suivre les ventes, stocks,
dépenses et estimations de rentabilité de trois activités. Le dépôt est la source
de vérité pour le code.

À lire avant toute modification :
- JED_conception_V3.md (décisions métier, sécurité, architecture et recette)
- workflow/README.md (méthode)
- workflow/PLAN.md, fiche [ID ET TITRE DE LA TÂCHE]
- workflow/DECISIONS.md pour les décisions métier confirmées et les questions éventuelles encore ouvertes
- les consignes locales éventuelles (AGENTS.md, instructions de l'outil) et le code existant

Tâche assignée : [ID ET TITRE]

Procède ainsi :
1. Inspecte l'état du dépôt et identifie les conventions déjà présentes. Ne suppose
   pas que la structure cible existe déjà.
2. Avant d'éditer, résume en quelques lignes le résultat attendu, les fichiers
   probablement concernés, les dépendances et tout point bloquant. N'attends pas
   de réponse pour les choix d'implémentation réversibles conformes aux documents.
3. Réalise uniquement cette tâche et ses changements indispensables. N'ajoute pas
   de fonctionnalités hors périmètre ou de dépendances sans justification.
4. Respecte les critères d'acceptation de sa fiche. Toute autorisation est vérifiée
   côté serveur et les données sont limitées à l'activité autorisée. Toute opération
   de stock/vente liée doit être cohérente en transaction. Les montants utilisent
   Decimal; les prix et coûts historiques d'une vente restent figés; les opérations
   validées sont corrigées par une opération traçable.
5. Si une décision métier non résolue affecte directement la tâche, ne la devine
   pas. N'implémente pas cette partie dépendante; explique la décision à prendre
   et termine seulement le travail indépendant qui reste utile.
6. Examine ton diff pour repérer les changements hors sujet, les secrets, les
   permissions manquantes et les effets sur les parcours existants. N'exécute pas
   de commande destructive. Ne crée pas de commit.

En fin de tâche, réponds avec :
- Résultat réalisé et fichiers modifiés;
- critères vérifiés et commandes/scénarios exécutés avec résultats (ou raison si
  une vérification n'a pas pu être faite);
- points bloquants, risques et décision métier attendue;
- proposition d'un message de commit, sans committer.
```

## Variantes rapides

- **Cline / Kilo Code** : choisir le mode qui peut modifier le dépôt uniquement après avoir vérifié le résumé de périmètre. Garder une seule tâche active; relire chaque diff avant d'accepter.
- **Copilot gratuit** : lui demander une sous-tâche bornée ou une revue en lecture seule. Si le contexte ne contient pas les documents, coller uniquement les règles pertinentes et la fiche de tâche; ne pas supposer qu'il les a lues.
- **Front-end design d'Anthropic** : utiliser uniquement pour une tâche de présentation UI; inclure les contraintes d'écran téléphone/PC et demander des templates/styles compatibles avec le projet déjà en place.
