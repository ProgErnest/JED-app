# Rapport d'audit JED

Date de l'audit : 30 octobre 2026  
Périmètre observé : application locale `http://127.0.0.1:8000`, compte gérant global déjà authentifié, base SQLite partagée en lecture seule.

## A. Synthèse exécutive

JED fournit une base opérationnelle réelle pour les trois activités : comptes et appartenances, catalogue distinct produits/prestations, tickets multi-lignes, entrées/corrections de stock, dépenses, annulations et indicateurs globaux/par activité. Les contrôles Django et la suite de 89 tests automatisés réussissent.

L’application n’est toutefois pas validée comme outil fiable de décision commerciale. Un tableau de rentabilité par produit a été ajouté après l’audit; il n’utilise que les coûts marqués fiables et ne permet pas de requalifier les historiques non fiables. Les activités ne disposent pas encore d’un résultat opérationnel complet. Les ventes historiques visibles ont des coûts snapshots mais toutes les lignes consultées sont marquées non fiables, d’où une marge brute fiable affichée nulle malgré des ventes. Le contrôle de stock et la navigation mobile ont également été corrigés depuis l’audit, sous réserve d’une validation de concurrence sur le backend cible et d’une vérification visuelle mobile.

Conformité fonctionnelle observée : PARTIAL. Conformité métier : PARTIAL, avec risques importants sur le contrôle du stock et l’analyse de rentabilité. UX responsive : PARTIAL. Aucun défaut CRITICAL n’a été prouvé dans le périmètre non destructif; deux constats HIGH requièrent une décision métier avant d’envisager une utilisation commerciale fiable. Ne pas déclarer l’application prête à la production sur la seule base de cet audit.

### Cartographie de l’implémentation

| Application | Responsabilité constatée |
|---|---|
| `activities` | Activités Restaurant-bar, Coiffure et Boutique |
| `accounts` | Comptes, rattachements et rôles GLOBAL, MANAGER, EMPLOYEE, contrôles d’accès |
| `catalog` | Produits physiques, prestations, unités personnalisables, historique des prix |
| `inventory` | Entrées, sorties, corrections/pertes et coût moyen pondéré |
| `sales` | Tickets multi-lignes, prix/coûts snapshots, annulations et restauration du stock |
| `expenses` | Dépenses par activité/catégorie, correction/annulation auditée |
| `analytics` | Indicateurs par activité et globaux, périodes, opérations récentes et résumé employé |

Le périmètre V1 ne montre pas de gestion de paiements partiels ou crédits, rendez-vous, recettes détaillées, salaires, fidélité, promotions, tickets imprimés ou notifications SMS/push; ces absences ne sont pas comptées comme anomalies.

## B. Matrice de conformité

| Fonctionnalité | Attendu | Résultat observé / preuve | Statut | Gravité |
|---|---|---|---|---|
| Vue propriétaire globale | Consolider les activités sans mélanger leurs opérations | Tableau par activité, somme globale et activité employé; données Boutique et Restaurant-bar séparées à l’écran | PASS | — |
| Chiffre d’affaires et tickets actifs | Exclure les ventes annulées | Le tableau global et l’activité excluent les tickets annulés; vente #38 apparaît annulée, seules les ventes actives sont agrégées | PASS | — |
| Dépenses et achats de stock | Distinction sans double comptage | Colonnes séparées; texte avertissant que le solde ventes-dépenses n’est pas un bénéfice comptable | PASS | — |
| Marge brute globale | Calcul sur coûts fiables, avec réserve | Lignes historiques non fiables toujours exclues; nouvelle vente snapshotte le coût avant sortie et garde la marge fiable si le coût est connu | PARTIAL (historiques non requalifiés) | MEDIUM |
| Analyse de rentabilité par produit | Quantité, CA, COGS, marge et taux par produit | Tableau produit par activité et période; COGS/marge/taux calculés seulement sur lignes fiables, coûts inconnus/non fiables distingués | CORRIGÉ (tests) | — |
| Produits sans vente / faible rotation | Identification explicite | Tous les produits du catalogue de l’activité listés avec stock actuel, quantité vendue et dernière vente ou « Jamais » | CORRIGÉ (tests) | — |
| Évolution, tendances et filtres de période | Aujourd’hui/semaine/mois/personnalisé | Période personnalisée par dates et bloc « Aujourd’hui »; aucun filtre prédéfini semaine/mois observé | PARTIAL | MEDIUM |
| Tableau par activité | Isoler les ventes, dépenses, marge | Activité choisie par URL et filtre; vues contrôlées côté serveur dans services/tests | PASS | — |
| Approvisionnement | Modifier stock et coût moyen | Formulaire ouvert; calcul pondéré et rollback démontrés par tests | PASS (tests) | — |
| Vente de produit | Décrémenter automatiquement le stock | Service de vente et tests confirment mouvements de sortie | PASS (tests) | — |
| Vente de prestation | Ne pas déclencher de stock | Test de service : coût nul, aucun mouvement de stock | PASS (tests) | — |
| Stock insuffisant | Refuser une vente impossible ou signaler sans ambiguïté | Refus dans le formulaire et le service transactionnel; tests couvrent quantité excessive, doublons et stock nul | PASS (tests après correction du 30/10/2026) | — |
| Annulation de vente | Exclure le CA, restaurer le stock, tracer | Service transactionnel, annulation idempotente et tests; ticket annulé visible dans l’historique | PASS (tests + UI) | — |
| Prix historiques | Ne pas modifier les ventes anciennes | Snapshots sur la ligne; test de changement de prix | PASS (tests) | — |
| Permissions serveur | Limiter par rôle et activité | Helpers et vues vérifient l’accès; tests 403/404 et filtrage employés | PASS (tests) | — |
| Navigation mobile | Accès lisible aux modules | Les liens passent sur plusieurs lignes sous 700 px; règle responsive vérifiée par test, validation visuelle navigateur non réalisée dans cette passe | CORRIGÉ (test CSS) | — |
| Absence de débordement horizontal du contenu | Mise en page utilisable en mobile/tablette | Mesures DOM : pas de débordement global du document aux tailles testées; tables en régions scrollables | PASS | — |
| Fonctionnement hors connexion, lecture seule | Lire données déjà chargées, bloquer écritures | Aucun mécanisme/offline cache identifiable dans l’interface parcourue ni dans les responsabilités visibles | NOT IMPLEMENTED | LOW |

## C. Anomalies détectées

### JED-AUD-01 — Marge invalide même pour le dernier article en stock

**Statut après corrections du 30/10/2026 : CORRIGÉ pour les nouvelles ventes; historiques inchangés.** Un test dédié confirme coût fiable et marge positive sur la dernière unité. Voir [RAPPORT_CORRECTIONS_JED.md](RAPPORT_CORRECTIONS_JED.md).

- Module : Ventes / Analytics.
- Gravité : HIGH.
- Description : `create_sale` effectue la sortie de stock avant de calculer `margin_reliable`; le test utilise le stock déjà décrémenté (`item.stock_quantity > 0`). Si la quantité vendue vide le stock, le coût pourtant connu avant la vente est écarté de l’indicateur de marge.
- Étapes/preuve : le test `test_create_sale_marking_stock_zero_has_unreliable_margin` part d’un stock de 1 et marque la vente non fiable après vente d’une unité. Les lignes actuelles ont des coûts snapshots renseignés mais `margin_reliable=False`; le dashboard affiche 0,00 FCFA de marge et avertit que les lignes sont exclues.
- Résultat attendu : une vente couverte par un coût unitaire connu avant le mouvement doit conserver un COGS/marge fiables; les situations réellement incertaines doivent rester explicitement exclues.
- Résultat obtenu : coût snapshot connu, mais contribution à la marge ignorée quand le stock tombe à zéro.
- Capture : [dashboard-activite-mobile-390x844.png](audit-captures/dashboard-activite-mobile-390x844.png).

### JED-AUD-02 — Ventes autorisées au-delà du stock disponible

**Statut après corrections du 30/10/2026 : CORRIGÉ dans le formulaire et le service métier.** Tests couvrent stock nul, quantité excessive et quantités répétées du même produit; aucune écriture n’a été faite sur la base de l’audit.

- Module : Ventes / Stock.
- Gravité : HIGH.
- Description : le stock peut devenir négatif et l’interface propose à la vente un produit de stock nul.
- Étapes/preuve : ouvrir Nouvelle vente Boutique; l’option « Bonbons · … · stock 0 » reste sélectionnable. Le test existant `test_create_sale_allows_negative_stock` valide une vente de 150 unités depuis un stock de 100 et aboutit à -50.
- Résultat attendu : selon la règle commerciale à confirmer, bloquer la vente en rupture ou exiger une confirmation explicite et produire une alerte fiable. Le comportement actuel n’empêche pas une vente impossible à servir et détériore la valorisation.
- Résultat obtenu : vente acceptée, stock négatif et marge déclarée non fiable.
- Capture : [vente-form-mobile-390x844.png](audit-captures/vente-form-mobile-390x844.png).

### JED-AUD-03 — Pas d’analyse de marge/rotation par produit

**Statut après correction : CORRIGÉ pour les nouveaux affichages de période, sous réserve de la fiabilité des snapshots historiques.** Le tableau activité liste les produits avec stock, quantité, chiffre d’affaires, COGS/marge/taux fiables, dernière vente et nombres de coûts inconnus/non fiables. Tests vérifient les invendus, la marge négative, l’annulation et le cloisonnement employé. Aucun backfill historique n’a été réalisé.

- Module : Analytics.
- Gravité : HIGH.
- Description observée lors de l’audit : le tableau « Articles vendus » fournissait quantités et recettes, sans coût des marchandises vendues, marge, taux de marge, dernière vente ni niveau de stock. Il n’incluait pas les produits sans ventes.
- Résultat attendu : distinguer volume, chiffre d’affaires, marge, stagnation et manque de données.
- Résultat obtenu lors de l’audit : impossible de déterminer ces éléments depuis les indicateurs alors disponibles. Le tableau ajouté après l’audit fournit désormais les métriques par produit, sous réserve de coûts fiables.
- Capture : [dashboard-activite-mobile-390x844.png](audit-captures/dashboard-activite-mobile-390x844.png).

### JED-AUD-04 — Navigation principale tronquée sur mobile

**Statut après correction : CORRIGÉ côté CSS responsive, avec test de non-régression de la règle flex-wrap.** Une validation visuelle navigateur aux tailles de l’audit reste à effectuer.

- Module : UX/UI global.
- Gravité : MEDIUM.
- Description observée lors de l’audit : à 390 × 844, la barre horizontale affichait seulement une partie des destinations; l’utilisateur devait deviner qu’elle défilait horizontalement. La largeur globale du document restait toutefois dans le viewport.
- Résultat attendu : navigation mobile repliée ou affordance claire et accessible.
- Résultat obtenu lors de l’audit : liens de navigation coupés au bord de l’écran. La règle CSS est depuis passée au retour à la ligne; un test automatisé la vérifie, sans validation visuelle navigateur dans cette passe.
- Capture : [dashboard-global-mobile-390x844.png](audit-captures/dashboard-global-mobile-390x844.png).

### JED-AUD-05 — Données historiques non valorisables dans l’état visible

- Module : Données / Analytics.
- Gravité : MEDIUM, à qualifier.
- Description : toutes les SaleLine consultées portent `margin_reliable=False`, y compris des lignes avec coût snapshot explicite; au moins un produit (Biscuits) affiche un coût moyen de 50 pour un prix de 25 et a une vente active. La marge attendue de cette ligne est -25 FCFA, mais le dashboard exclut la ligne et présente 0 de marge.
- Résultat attendu : l’utilisateur doit distinguer marge négative, coût inconnu et coût non fiable.
- Résultat obtenu : ces cas sont confondus dans la marge exclue; pas de tableau de bord produit permettant de diagnostiquer la perte.
- Note : cet état peut provenir de données créées avant l’instrumentation du coût fiable. Il est donc signalé comme qualité/traçabilité des données, pas comme preuve d’une erreur de calcul sur chaque vente.

## D. Audit financier

Les coûts sont modélisés en coût moyen pondéré et snapshotés sur les lignes de vente. Test de cohérence existant : stock initial 10 à 2,00, entrée de 10 à 4,00 produit un coût moyen 3,00; ce scénario équivaut au principe attendu d’une moyenne pondérée. Les entrées successives, stock négatif et rollback du mouvement sont couverts par tests.

Le scénario demandé 10 × 1 000 FCFA puis 10 × 1 500 FCFA, vente de 5 × 2 000 FCFA, n’a pas été exécuté dans le navigateur afin de préserver la base partagée. Résultat mathématique attendu : coût moyen 1 250 FCFA, CA 10 000 FCFA, COGS 6 250 FCFA, marge brute 3 750 FCFA, taux sur CA 37,5 %. Le calcul théorique est cohérent avec le service; le rendu réel de ce scénario reste non vérifié de bout en bout.

Les indicateurs globaux sont additionnés par activité. Achats et dépenses sont séparés. « Après dépenses déclarées » correspond à CA moins dépenses uniquement, et l’interface précise correctement que ce n’est pas un bénéfice comptable. Le COGS et le résultat opérationnel complet (marge brute moins dépenses) ne sont pas affichés comme métriques dédiées.

Échantillon réel consulté en lecture seule sur la période 01–30/10/2026 : Boutique CA 25 FCFA, 1 ticket actif, dépenses 0, achats 10 000 FCFA, marge estimée 0; Coiffure CA 0; Restaurant-bar CA 154,50 FCFA et 6 tickets. Total CA 179,50 FCFA, somme des trois activités. Les achats/ventes visibles dans cet échantillon ne constituent pas une simulation contrôlée et ne permettent pas de conclure à la performance commerciale.

## E. Audit UX/UI

- Le tableau de bord global et celui d’activité présentent une hiérarchie claire, des libellés de prudence financière, des tableaux détaillés et des états vides.
- Navigation : desktop utilisable; mobile 390 × 844 tronqué horizontalement. Capture fournie.
- Mise en page : aucune largeur de document excédant le viewport mesurée à 1440 × 900, 768 × 1024 et 390 × 844 sur le tableau d’activité. Les tableaux se présentent comme régions scrollables.
- Formulaire de vente : champs lisibles, plusieurs lignes possibles, prix snapshots explicités; l’option de produit à stock nul est néanmoins un risque fonctionnel.
- Formulaire d’approvisionnement : champs produit, quantité, coût unitaire et motif présents. Capture : [entree-stock-mobile-390x844.png](audit-captures/entree-stock-mobile-390x844.png).
- Captures disponibles : [dashboard-global-desktop-1440x900.png](audit-captures/dashboard-global-desktop-1440x900.png), [dashboard-global-mobile-390x844.png](audit-captures/dashboard-global-mobile-390x844.png), [dashboard-activite-mobile-390x844.png](audit-captures/dashboard-activite-mobile-390x844.png), [vente-form-mobile-390x844.png](audit-captures/vente-form-mobile-390x844.png), [entree-stock-mobile-390x844.png](audit-captures/entree-stock-mobile-390x844.png).

## F. Permissions et intégrité

Les rôles GLOBAL, MANAGER et EMPLOYEE sont explicitement modélisés. Les contrôles côté serveur filtrent les opérations d’un employé à ses propres données, limitent l’accès par activité et réservent le tableau global au gérant global. Les tests de permissions ventes, stock, équipe et tableau de bord couvrent les refus et filtrages, notamment l’accès direct aux détails d’une vente d’un collègue.

Les créations de ventes et mouvements de stock sont atomiques. L’annulation d’une vente restaure le stock via mouvements correctifs, ne supprime pas le ticket et est idempotente selon les tests. Les annulations de dépenses sont journalisées. Les produits utilisés sont protégés contre la suppression physique par les mouvements.

Les limites importantes sont le stock négatif autorisé et le marquage de marge fiable effectué après sortie. Le test concurrent réel sur SQLite / Render n’a pas été réalisé. La garantie de `select_for_update` dépend du backend et SQLite ne fournit pas les mêmes garanties de verrouillage qu’un SGBD serveur; le déploiement cible doit tester la concurrence spécifiquement.

## G. Évaluation de l’aide à la décision

| Question | Réponse | Preuve |
|---|---|---|
| Le propriétaire peut-il connaître la situation financière globale ? | Partiellement | CA, dépenses, achats, marge estimée et solde indicatif affichés; COGS et résultat opérationnel complet absents. |
| Peut-il comparer les trois activités ? | Oui, pour CA/ventes/dépenses/achats et estimations actuelles | Tableau global par activité et total arithmétique. |
| Peut-il identifier les produits rentables ? | Partiellement | Le nouveau tableau affiche marge/taux sur les seules lignes fiables; les snapshots historiques non fiables restent exclus. |
| Peut-il détecter les produits qui stagnent ? | Oui, partiellement | Les produits sans vente de période sont listés et leur dernière vente active ou « Jamais » est affichée. |
| Peut-il identifier les produits à faible marge ? | Partiellement | Marge et taux par produit sont disponibles lorsque des lignes fiables existent; aucune recommandation automatique n’est faite. |
| Peut-il prendre des décisions commerciales pertinentes ? | Partiellement | Le tableau produit apporte stock, rotation et marge fiable; qualité des données historiques et résultat opérationnel complet restent limitants. |

Avec les données actuellement consultées, on ne peut pas justifier un réapprovisionnement, un retrait de catalogue ni déterminer quelle activité est la plus rentable. On peut uniquement identifier les recettes de période, certains volumes et coûts d’approvisionnement enregistrés séparément.

## H. Plan de correction priorisé

1. **Stock et ventes (HIGH)** : corrigé et testé dans le service, le formulaire, les mouvements et les annulations; valider encore la concurrence sur le backend de déploiement.
2. **Fiabilité financière (HIGH)** : corrigé et testé pour les nouvelles ventes; ne pas requalifier les snapshots historiques sans stratégie validée.
3. **Rentabilité produit (HIGH)** : tableau de période par produit ajouté et testé. Les lignes non fiables sont visibles séparément et ne contribuent pas à la marge fiable; aucune recommandation commerciale n’est produite.
4. **Permissions et intégrité (MEDIUM, validation ciblée)** : compléter le test navigateur des rôles et les tests de courses concurrentes sur le backend réellement déployé.
5. **Fonctionnel (MEDIUM)** : ajouter filtres prédéfinis aujourd’hui/semaine/mois si requis par le besoin; tester corrections, annulations, erreurs de validation et double soumission dans un staging.
6. **UX/UI (MEDIUM)** : navigation mobile passée au retour à la ligne et règle CSS testée; valider visuellement les tailles mobiles réelles. Le stock courant est affiché dans le tableau de rentabilité.
7. **Améliorations secondaires** : alertes de stock et d’activité inerte, tendance de vente et exports seulement après validation des métriques sources.

## Méthode, limites et validation

- Interface parcourue en navigateur authentifié : tableau global, tableau Boutique, liste et formulaire de vente, formulaire d’entrée de stock. Aucun formulaire n’a été soumis.
- Captures prises aux tailles demandées; contrôle DOM responsive effectué sur la page activité aux trois tailles.
- État de la base actuelle lu uniquement; aucune donnée métier créée, modifiée ou supprimée.
- Contrôles initiaux de l’audit : `manage.py test` (89 tests), `manage.py check` et `makemigrations --check --dry-run` réussis. Après correctifs : `manage.py test` (100 tests, OK), `manage.py check` sans problème et `makemigrations --check --dry-run` sans migration en attente.
- Les tests automatisés prouvent les services et permissions couverts, mais ne remplacent pas des scénarios de bout en bout dans un staging. Le scénario contrôlé complet à trois activités, les opérations réellement soumises, les validations navigateur, les accès avec sessions Manager/Employee et le déploiement Render restent BLOCKED pour cet audit faute d’environnement de recette isolé et d’autorisation d’écriture.