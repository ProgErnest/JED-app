# Rapport des corrections JED

Date de clôture des correctifs : 2 novembre 2026  
Référence : [RAPPORT_AUDIT_JED.md](RAPPORT_AUDIT_JED.md)  
Périmètre : corrections JED-AUD-01 à JED-AUD-04, sans modification de données métier existantes.

## 1. Anomalies corrigées

### JED-AUD-01 — Fiabilité du coût et de la marge

Corrigée pour les nouvelles ventes. Le coût et son statut sont déterminés avant le mouvement de sortie. Une vente qui consomme la dernière unité garde donc son coût et sa marge fiables lorsque le stock et la valorisation sont connus avant la vente. Un coût non déterminable est enregistré `NULL` et affiché « Inconnu »; un coût connu mais non fiable reste visible comme tel; une marge négative fiable conserve son signe négatif.

Preuves : tests de vente de la dernière unité, du coût inconnu, de la marge négative et du scénario chiffré coût moyen pondéré. Les snapshots `unit_price` et `cost` des tickets restent immuables après enregistrement.

### JED-AUD-02 — Dépassement de stock

Corrigée dans les deux couches. Les produits à stock nul sont exclus des choix du formulaire. Une validation du formulaire rejette aussi une quantité supérieure au stock affiché. Le service `create_sale` recharge les produits sous verrou dans la transaction, agrège toutes les lignes par produit et refuse le ticket avant création si la demande totale dépasse le stock disponible. Le contrôle métier reste donc effectif pour les appels serveur directs et les lignes dupliquées.

La transaction atomique est conservée. En cas de refus, aucun ticket ni mouvement de sortie n’est enregistré. Les prestations restent vendables sans mouvement de stock.

### JED-AUD-03 — Rentabilité et rotation par produit

Corrigée dans le tableau de bord d’activité. Pour chaque produit du catalogue, le tableau affiche stock courant, quantité vendue et chiffre d’affaires sur la période, dernière vente, COGS/marge/taux calculés uniquement sur les lignes dont `margin_reliable` est vrai, et nombres de coûts inconnus ou non fiables. Les ventes annulées sont exclues; les employés ne voient que leurs propres ventes. Les produits sans vente apparaissent avec quantité zéro et dernière vente « Jamais ». Une marge négative fiable conserve son signe; aucun coût historique non fiable n’est requalifié.

Preuves : tests d’agrégation et de rendu couvrant invendus, marge négative, lignes inconnues/non fiables, annulation et périmètre employé.

### JED-AUD-04 — Navigation mobile

Corrigée côté CSS : sous 700 px, les destinations de navigation se replient sur plusieurs lignes et ne dépendent plus d’un défilement horizontal implicite. Un test de non-régression vérifie cette règle responsive. Le rendu visuel réel à 390 px n’a pas été vérifié dans un navigateur pendant cette passe.

## 2. Fichiers portant les corrections

Les fichiers suivants portent les correctifs appliqués dans cette intervention; les modifications locales préexistantes sans lien ont été laissées intactes.

- `apps/sales/services.py` : validation serveur du stock, cumul des quantités par produit, verrouillage transactionnel et snapshot du coût avant sortie.
- `apps/sales/forms.py` : exclusion des produits épuisés et validation de quantité par ligne.
- `apps/sales/views.py` : transmission à l’interface des seuls produits actifs en stock; erreurs métier affichées sans créer de ticket.
- `apps/sales/models.py` : coût nullable pour représenter un coût inconnu; marge calculée sans neutraliser les valeurs négatives.
- `templates/sales/sale_detail.html` : distinction visuelle entre coût/marge inconnus, marge non fiable et marge calculable, y compris négative.
- `apps/sales/tests/test_sales.py` : tests du service, formulaire, vues, stock, coûts, annulations et permissions.
- `apps/sales/migrations/0004_alter_saleline_cost.py` : migration additive du champ `cost` en nullable, sans opération de données.
- `apps/analytics/services.py` : agrégation par produit et période, en excluant les ventes annulées et en respectant le périmètre employé.
- `apps/analytics/tests/test_services.py` : tests des invendus, marge négative, fiabilité des coûts et portée employé.
- `apps/analytics/tests/test_views.py` : tests de rendu du tableau et de la règle responsive.
- `templates/analytics/activity_dashboard.html` : tableau de rentabilité/rotation par produit.
- `static/css/jed.css` : retour à la ligne des destinations de navigation mobile.
- `RAPPORT_AUDIT_JED.md` : statut des constats prioritaires dans le rapport d’audit.
- `RAPPORT_CORRECTIONS_JED.md` : présent rapport de clôture.

## 3. Règles métier appliquées

- Vente refusée si quantité totale par produit supérieure au stock disponible.
- Produit à stock nul non proposé comme article vendable.
- Validation obligatoire dans le service métier, indépendamment du formulaire.
- Coût snapshoté depuis l’état avant sortie.
- Coût nul n’est considéré connu que si l’historique d’approvisionnement prouve une entrée valorisée à zéro; sans coût connu, la ligne reçoit `cost=None` et n’a pas de marge calculable.
- Service : coût connu de zéro et absence de sortie de stock.
- Marge négative fiable conservée telle quelle; aucune conversion en zéro.
- Les lignes ayant plusieurs occurrences d’un même produit sont validées sur leur quantité cumulée.
- Annulation conservée : elle ne repasse pas par le contrôle de vente et restaure le stock via le mécanisme existant.

## 4. Tests exécutés et résultats

Résultats de clôture, exécutés avec l’environnement `.venv` du workspace :

- `manage.py test apps.sales.tests.test_sales -v 2` : 55 tests réussis. Cela couvre notamment le coût fiable de la dernière unité, les coûts inconnus, la marge négative, le refus de stock insuffisant (y compris les lignes répétées), l’exclusion du stock nul, les mouvements, les annulations et les accès de vente.
- Tests analytics ciblés : 4 tests couvrent les invendus, marge négative, coûts non fiables/inconnus, portée employé, rendu de page et règle de navigation.
- `manage.py test` : 100 tests réussis; suite complète et vérifications système de Django sans erreur.
- `manage.py check` : aucun problème.
- `manage.py makemigrations --check --dry-run` : aucune migration supplémentaire détectée.
- Test financier inclus dans les tests de vente : coût moyen 1 250 FCFA; chiffre d’affaires 10 000 FCFA; COGS 6 250 FCFA; marge brute 3 750 FCFA; taux de marge sur chiffre d’affaires 37,5 %.

Les tests sont exécutés sur la base de test Django isolée. Les tests de mouvements prouvent le déstockage au moment de la vente et la restauration lors de l’annulation; les tests de permissions de la suite complète restent verts. Aucun scénario n’a écrit dans la base métier locale ou dans une base de production.

## 5. Migration

Migration additive `0004_alter_saleline_cost` : `SaleLine.cost` devient nullable et son défaut est `None`. Elle ne contient aucune `RunPython`, suppression de colonne ou réinterprétation de données. Le test runner applique les migrations sur sa base temporaire. La migration n’a pas été appliquée à la base métier locale pendant ce travail.

Les coûts, prix et drapeaux `margin_reliable` historiques ne sont pas modifiés. On ne peut pas inférer rétroactivement si un ancien zéro représente un coût réellement gratuit ou une donnée absente; les anciennes lignes non fiables restent donc non fiables et leurs marges restent exclues.

## 6. Anomalies restantes

- JED-AUD-03 : corrigée pour les métriques produit des nouvelles vues, mais les lignes historiques marquées non fiables restent exclues; leur qualification demande une stratégie de données distincte.
- JED-AUD-04 : correction CSS testée; validation visuelle sur navigateur aux tailles mobiles de référence encore à effectuer.
- JED-AUD-05 : données historiques non valorisables à qualifier; aucune réparation automatique effectuée.
- Fonctionnement hors connexion lecture seule : non implémenté d’après l’audit; hors périmètre des corrections prioritaires.
- Les filtres prédéfinis semaine/mois et les tests navigateur multi-rôles restent à vérifier.

## 7. Risques et limites

- SQLite ne fournit pas les mêmes garanties de verrouillage que les bases serveur. Le service utilise `select_for_update` dans une transaction; le comportement de concurrence doit être testé sur l’environnement réel d’hébergement avant exploitation simultanée.
- Les objets de test utilisent une base isolée; aucune opération métier n’a été soumise à l’application connectée à la base partagée.
- Les données déjà en stock avec coût moyen zéro et sans mouvement d’entrée ne sont pas requalifiables de façon certaine. Elles sont traitées comme coût inconnu pour les nouvelles ventes.
- Les annulations historiques restent inchangées; leurs mouvements de restauration peuvent rétablir les quantités, mais ne constituent pas une preuve du coût d’origine.

## Validation finale

Les anomalies JED-AUD-01 à JED-AUD-04 disposent de tests ciblés et la suite complète passe. Pour JED-AUD-04, la preuve porte sur la règle CSS et non sur une capture navigateur. La migration `sales.0004_alter_saleline_cost` est déjà présente et s’applique dans la base temporaire du test runner; `makemigrations --check --dry-run` ne signale aucun changement supplémentaire. Elle n’a pas été appliquée à la base métier locale pendant cette intervention.