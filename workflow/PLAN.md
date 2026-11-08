# Plan de travail JED

Les fiches ci-dessous découpent les phases du document de conception en changements relisibles. Les chemins sont indicatifs au démarrage : l'agent inspecte le dépôt et respecte l'architecture finalement retenue. Ne marquez une tâche terminée qu'après revue et vérification des critères.

## Ordre et tâches

### JED-01 — Socle Django et configuration

- **Dépend de** : aucune. **Priorité** : P0.
- **Résultat** : dépôt Git initialisé s'il ne l'est pas déjà, projet qui démarre localement, SQLite configurée, réglages de développement distincts de ceux de production, dépendances déclarées et instructions de lancement.
- **Fichiers visés** : `manage.py`, `config/`, `requirements.txt`, `.gitignore`, documentation de lancement.
- **Règles** : secrets hors du dépôt; `DEBUG` et hôtes de production configurables sans valeur secrète codée en dur; ne pas ajouter de framework front-end.
- **Acceptation** : si Git n'était pas initialisé, le dépôt l'est; installation propre selon les instructions, migrations initiales exécutables, serveur de développement accessible; aucun secret ou fichier de base local suivi par Git.
- **Commit suggéré** : `chore: initialise le socle Django`

### JED-02 — Comptes, activités et appartenances

- **Dépend de** : JED-01. **Priorité** : P0.
- **Résultat** : utilisateurs, activités Restaurant-bar/Coiffure/Boutique configurables et appartenance utilisateur-activité avec rôle.
- **Fichiers/modèles visés** : `apps/accounts/`, `apps/activities/`, `User`, `Activity`, `ActivityMembership` (ou regroupement cohérent documenté).
- **Règles** : un gérant global voit les trois activités; rôles d'activité sont limités à leur activité. La gestion des comptes par un responsable dépend de A2.
- **Acceptation** : migrations et données initiales reproductibles; rattachements explicites; pas d'accès implicite à une activité.
- **Décision métier** : A2 est tranchée; le responsable peut gérer les accès de son activité. La désactivation complète du compte est réservée au gérant global.
- **Commit suggéré** : `feat: ajoute les comptes et activités`

### JED-03 — Autorisations et périmètre des données

- **Dépend de** : JED-02. **Priorité** : P0.
- **Résultat** : règles d'accès centralisées et appliquées côté serveur aux vues et requêtes.
- **Fichiers/modèles visés** : `apps/accounts/`, utilitaires de permissions, vues de test manuel/documentation.
- **Règles** : employé limité à ses opérations selon A3; responsable limité à son activité; gérant global à toutes. Masquer un lien ne protège pas une URL.
- **Acceptation** : pour chaque rôle, l'accès autorisé fonctionne et l'accès interdit (y compris URL directe et changement d'identifiant) est refusé; aucune fuite entre activités.
- **Blocage métier** : trancher A3 avant de fixer les vues de consultation des dépenses et corrections.
- **Commit suggéré** : `feat: applique les permissions par rôle`

### JED-04 — Catalogue, services et historique des prix

- **Dépend de** : JED-02 et JED-03. **Priorité** : P0.
- **Résultat** : création et modification de produits/services, prix, unité de référence et conditionnement si nécessaire.
- **Fichiers/modèles visés** : `apps/catalog/`, `Product`, `Service`, unités, historique/audit des prix.
- **Règles** : produits rattachés à une activité; pas de consommation automatique pour les prestations de coiffure; prix modifié historisé; les opérations passées gardent leur prix. Le statut brouillon/actif dépend de A8.
- **Acceptation** : chaque rôle autorisé peut créer/consulter dans son périmètre; changement de prix conserve l'ancien historique et n'altère aucune vente antérieure.
- **Décision métier** : A8 est tranchée; les articles créés sont actifs immédiatement, sans approbation préalable.
- **Commit suggéré** : `feat: ajoute le catalogue des produits et services`

### JED-05 — Approvisionnements et coût moyen

- **Dépend de** : JED-04. **Priorité** : P0.
- **Résultat** : entrée de stock avec quantité, coût, date, auteur, mouvement traçable et mise à jour du coût moyen.
- **Fichiers/modèles visés** : `apps/inventory/`, `StockMovement`, service central de stock, champs de coût moyen.
- **Règles** : achat de stock distinct d'une dépense générale; montants en `Decimal`; chaque entrée et mise à jour atomiques; application de la formule de coût moyen du document lorsque son cas s'applique.
- **Acceptation** : approvisionnements successifs donnent le coût moyen attendu; mouvement, quantité et coût correspondent; échec en cours d'opération ne laisse pas de mise à jour partielle.
- **Décision métier** : A4 est tranchée; lorsqu'une entrée ramène le stock au-dessus de zéro, le coût moyen repart du coût unitaire de cette entrée, sans inclure la quantité négative. Si le stock reste nul ou négatif, la marge reste signalée comme non fiable.
- **Commit suggéré** : `feat: enregistre les approvisionnements et coûts moyens`

### JED-06 — Corrections et inventaire de stock

- **Dépend de** : JED-05. **Priorité** : P0 pour corrections; inventaire complet P1.
- **Résultat** : mouvements de correction/perte avec motif, auteur et date; historique consultable. Inventaire hebdomadaire complet seulement après les flux P0.
- **Fichiers/modèles visés** : `apps/inventory/`, formulaires/vues, journal d'audit.
- **Règles** : aucune modification directe du stock hors service central; motif obligatoire; mouvement inverse plutôt que suppression; suivre la règle de concurrence d'inventaire de conception si P1 est réalisé.
- **Acceptation** : stock calculable depuis l'historique; correction visible avec son motif; vérification d'un inventaire ne peut être appliquée deux fois.
- **Commit suggéré** : `feat: ajoute les corrections traçables de stock`

### JED-07 — Ventes et lignes historiques

- **Dépend de** : JED-03, JED-04 et JED-05. **Priorité** : P0.
- **Résultat** : vente individuelle et groupée, lignes d'articles, total, auteur, date, prix appliqué et coût retenu figés; sorties de stock liées dans la même transaction.
- **Fichiers/modèles visés** : `apps/sales/`, `Sale`, `SaleLine`, services de vente et mouvements de stock.
- **Règles** : `Decimal`; prestation sans mouvement de stock; prix historique immuable; vente sur stock insuffisant autorisée avec avertissement; marge signalée peu fiable si stock négatif. Mélange produit/prestation en vente groupée dépend de A7.
- **Acceptation** : total des lignes égal au total de vente; auteur/horodatage corrects; bonne sortie par produit; panne sur une ligne annule l'ensemble; ventes passées inchangées après changement de prix.
- **Décisions métier** : A6 et A7 sont tranchées; boutique et coiffure ont des produits revendus suivis en stock, et une vente groupée peut mêler produits et prestations.
- **Commit suggéré** : `feat: enregistre les ventes et leurs mouvements`

### JED-08 — Annulations, corrections et audit métier

- **Dépend de** : JED-07. **Priorité** : P0.
- **Résultat** : annulation de vente avec motif et mouvement de stock inverse; journal consultable des opérations sensibles.
- **Fichiers/modèles visés** : `apps/audit/`, `apps/sales/`, service d'annulation.
- **Règles** : opération initiale conservée; annulation idempotente; auteur/date/motif enregistrés; accès au journal selon le rôle et l'activité.
- **Acceptation** : vente annulée exclue des totaux, historique intact, stock rétabli une seule fois et opération d'annulation attribuable.
- **Commit suggéré** : `feat: trace les annulations de vente`

### JED-09 — Dépenses catégorisées

- **Dépend de** : JED-02 et JED-03. **Priorité** : P0.
- **Résultat** : saisie de dépenses par catégorie et activité; correction/annulation historisées.
- **Fichiers/modèles visés** : `apps/expenses/`, `Expense`, catégories, audit.
- **Règles** : achats alimentant le stock exclus des dépenses générales; montants en `Decimal`; auteur et date conservés; saisie de dépenses par tout employé conformément à la conception. Le moment de prise en compte dépend de A5.
- **Acceptation** : dépense catégorisée incluse selon son statut métier; correction traçable; aucun double comptage d'un approvisionnement.
- **Décision métier** : A5 est tranchée; une dépense est comptée à la saisie, et corrections/annulations sont traçables.
- **Commit suggéré** : `feat: ajoute le suivi des dépenses`

### JED-10 — Indicateurs et tableaux de bord essentiels

- **Dépend de** : JED-07, JED-08 et JED-09. **Priorité** : P0.
- **Résultat** : ventes, nombre d'opérations, marge estimée disponible, dépenses et vues limitées par rôle; chiffres du gérant global par activité.
- **Fichiers/modèles visés** : `apps/analytics/`, vues/templates des tableaux de bord.
- **Règles** : ventes annulées exclues; pas de présentation en bénéfice net comptable; coiffure basée sur recettes et dépenses déclarées; périmètre filtré côté serveur.
- **Acceptation** : sommes comparées manuellement aux ventes non annulées de la période; les rôles ne voient que leur périmètre; libellés signalent les estimations.
- **P1 éventuel** : comparaisons personnalisées, produits sans vente, alertes et analyse détaillée employés.
- **Commit suggéré** : `feat: ajoute les tableaux de bord essentiels`

### JED-11 — Interface responsive et parcours prioritaires

- **Dépend de** : flux fonctionnels disponibles des tâches JED-02 à JED-10. Peut être intégrée progressivement à celles-ci.
- **Résultat** : parcours utilisables sur téléphone et PC pour connexion, catalogue, entrée/correction de stock, vente, dépense et consultation des indicateurs.
- **Fichiers visés** : templates Django, CSS et éléments statiques déjà choisis.
- **Règles** : formulaires adaptés à la saisie réelle; retours de validation clairs; autorisations côté serveur conservées; limiter les dépendances.
- **Acceptation** : parcours essentiels navigables sur téléphone et ordinateur; erreurs de formulaire compréhensibles; aucun bouton ou style ne remplace les contrôles serveur.
- **Commit suggéré** : `feat: construit les parcours web responsive`

### JED-12 — Recette, sauvegardes, restauration et déploiement

- **Dépend de** : flux P0 terminés (JED-01 à JED-11). **Priorité** : P0.
- **Résultat** : configuration de production sécurisée, sauvegarde quotidienne hors serveur si possible, procédure documentée, restauration vérifiée et déploiement accessible.
- **Fichiers visés** : configuration Django, scripts ou procédure d'exploitation, `DEPLOYMENT.md`/guide utilisateur.
- **Règles** : persistance SQLite vérifiée chez l'hébergeur; secrets en variables d'environnement; HTTPS, `DEBUG` désactivé, hôtes autorisés; ne jamais inclure de base réelle/secrets dans Git.
- **Acceptation** : scénarios de recette du document exécutés; sauvegarde restaurée sur copie de test avec données récupérées; application testée depuis un autre appareil.
- **Commit suggéré** : `chore: prépare la production et les sauvegardes`

### JED-13 — Rubriques de catalogue et filtres de caisse

- **Dépend de** : JED-04 et JED-07. **Priorité** : P1.
- **Résultat** : classement des produits et prestations par rubriques propres à chaque activité, filtrage des catalogues et de la caisse, avec exemples de référence optionnels.
- **Fichiers/modèles visés** : `apps/catalog/` (`CatalogCategory`, formulaires, vues, service et commande de seed), `apps/sales/` (contexte de caisse), templates catalogue/vente et `static/css/jed.css`.
- **Règles** : catégorie facultative pour préserver les données existantes; catégories et articles cloisonnés par activité; produits/prestations déjà rattachés restent visibles quand une catégorie est désactivée; prix des références indicatifs, aucun prix de pack présenté comme prix unitaire; seed explicite, idempotent, dry-run, sans écrasement des données ou création de stock/ventes fictifs.
- **Acceptation** : création/modification contrôlée selon le rôle et l'activité; filtres rubrique/recherche utilisables sur desktop et mobile; anciennes entrées non classées accessibles; migration additive; tests permissions, catégories inactives, seed répétée et absence d'écrasement de prix.
- **Commit suggéré** : `feat: classe les produits et prestations par rubrique`

## Ordre de repli

En cas de retard : terminer les parcours de vente, stock, dépenses, permissions et audit; réduire d'abord les tâches P1 du tableau de bord et l'inventaire complet. Ne pas raccourcir la recette de permissions ni sauter le test de restauration avant la livraison.
