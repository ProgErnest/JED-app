# JED — Conception fonctionnelle et plan de livraison

**Version 3.0 — 26 octobre 2026**
Application de gestion des stocks, des ventes et du suivi de rentabilité — JED, Bafoussam

| Élément | État |
|---|---|
| Statut | Base de travail consolidée : décisions de la V2 + plan d'implémentation de la V1 |
| Activités couvertes | Restaurant-bar, coiffure et boutique dès la V1 |
| Objectif principal | Mesurer les ventes, estimer les marges, suivre les dépenses et aider le gérant à décider |
| Échéance | 3 novembre 2026 |
| Budget maximal | 200 000 FCFA, hébergement et domaine compris |
| Stack | Django + SQLite ; interface web responsive (téléphone et PC) |
| Devise des opérations | FCFA (XAF) |
| Point de départ | Développement from scratch (aucun code existant) |

---

## 1. Résumé exécutif

JED n'est pas un simple registre de stock. Il donne au gérant une vision fiable des opérations et de la performance des trois activités. Le gérant peut :

- consulter les ventes depuis le début de la journée ;
- repérer les activités ou produits sans ventes enregistrées ;
- examiner les opérations par auteur ;
- comparer les résultats entre périodes.

La fiabilité des indicateurs dépend de la qualité des saisies : prix appliqué à la vente, coût des produits, entrées de stock, corrections, annulations et dépenses. Les résultats affichés sont des **estimations de gestion**, jamais un bénéfice net comptable certifié, tant que toutes les charges ne sont pas suivies.

**Principe directeur de la V1** : livrer une application cohérente et réellement utilisable, pas une application riche en écrans mais peu fiable sur les calculs, les permissions ou les mouvements de stock.

**Règle de repli** : le délai est de 8 jours calendaires (du 26 octobre au 3 novembre), soit un plan intensif. Si une phase prend du retard, on réduit les fonctions secondaires (P1, P2). On ne supprime jamais les contrôles d'accès, l'intégrité des ventes ni les sauvegardes.

---

## 2. Objectifs et indicateurs

- Suivre les ventes par activité, employé, produit/prestation et période.
- Estimer la marge des produits revendus à partir du coût moyen d'achat.
- Pour la coiffure, comparer les recettes enregistrées et les dépenses déclarées, sans coût détaillé par prestation.
- Identifier les produits sans ventes sur une période et suggérer un réexamen, sans suppression automatique.
- Permettre au gérant global de repérer l'absence de ventes enregistrées, sans conclure que l'activité réelle est nulle.
- Assurer la traçabilité des mouvements de stock, corrections, annulations, prix et dépenses.

### Définition des indicateurs

| Indicateur | Définition |
|---|---|
| Chiffre d'affaires | Ventes enregistrées, hors ventes annulées |
| Marge estimée d'un produit | Calculée avec le coût d'achat moyen figé sur la ligne de vente |
| Dépenses générales | Suivies séparément des approvisionnements |
| Résultat de la coiffure | Estimation fondée sur les recettes et dépenses effectivement saisies |

---

## 3. Périmètre de livraison (priorités)

| Priorité | Module | Résultat attendu |
|---|---|---|
| P0 | Authentification et autorisations | Chaque utilisateur accède uniquement aux fonctions et activités permises par son rôle |
| P0 | Activités | Trois activités configurables, données séparées |
| P0 | Produits et services | Création, consultation, modification des produits, services, prix et unités |
| P0 | Ventes | Ventes individuelles et groupées, prix appliqué conservé au moment de la vente |
| P0 | Stock | Entrées, sorties liées aux ventes, corrections justifiées, écarts d'inventaire, historique des mouvements |
| P0 | Dépenses | Enregistrement, catégorisation, correction et annulation traçables |
| P0 | Rentabilité | Chiffre d'affaires et marges estimées calculés à partir des données enregistrées |
| P0 | Tableau de bord | Indicateurs du gérant global ; vues limitées aux activités pour les responsables |
| P0 | Historique | Auteur, date, motif des corrections et annulations |
| P0 | Sauvegardes | Sauvegarde de la base et procédure de restauration vérifiée |
| P0 | Déploiement | Application en ligne, configuration sécurisée |
| P1 | Inventaire hebdomadaire complet | Comptage, validation unique, traitement des mouvements concurrents |
| P1 | Comparaisons avancées | Comparaisons entre périodes et périodes personnalisées |
| P1 | Alertes et analyses | Produits sans ventes, dernières ventes, alertes de stock, suivi de l'activité des employés |
| P2 | Améliorations ultérieures | Fonctions non indispensables à l'exploitation initiale |

Les priorités P1 et P2 ne retardent jamais les flux P0. Elles sont intégrées si les tests démontrent que le socle est stable.

### Reporté après la V1

- mode hors ligne (lecture seule et saisie) ;
- notifications SMS ou WhatsApp ;
- gestion des ingrédients et des recettes de cuisine ;
- consommation automatique des produits utilisés en coiffure ;
- rapports très détaillés et exports avancés ;
- toute intégration qui ne contribue pas directement aux ventes, aux stocks, aux dépenses ou aux permissions.

---

## 4. Décisions métier validées

| Nº | Décision | Règle retenue |
|---|---|---|
| 1 | Activités de la V1 | Restaurant-bar, coiffure et boutique |
| 2 | Saisie des ventes | Au moment de la transaction ; saisie individuelle et groupée autorisées |
| 3 | Auteur des ventes | Chaque employé enregistre les ventes sur son propre compte |
| 4 | Absence de ventes | Afficher « aucune vente enregistrée depuis 8 h » ; ne pas l'assimiler à une absence d'activité réelle |
| 5 | Vue du gérant global | Ventes détaillées, produits/quantités/montants, mouvements de stock, corrections, chronologie et auteur |
| 6 | Analyse de performance | Quantités, chiffre d'affaires, marge estimée et comparaison de périodes |
| 7 | Ventes groupées | Autoriser ventes individuelles et groupées compatibles |
| 8 | Coût des produits | Coût moyen d'achat calculé à partir des entrées de stock |
| 9 | Coiffure | Pas de coût par prestation ; comparer recettes et dépenses déclarées sur une période |
| 10 | Comparaisons | Périodes prédéfinies et période personnalisée |
| 11 | Produits sans ventes | Signaler, montrer la dernière vente connue, suggérer une réévaluation ; aucune suppression automatique |
| 12 | Unités de stock | Unité de référence et conditionnement configurable (ex. caisse de 12 bouteilles) |
| 13 | Stock négatif | Vente autorisée au-delà du stock, avec avertissement ; la marge est signalée « indisponible ou peu fiable » tant que le stock n'est pas régularisé. Si une entrée fait repasser le stock au-dessus de zéro, le coût moyen repart du coût unitaire de cette entrée, sans inclure la quantité négative dans le calcul. Les vérifications régulières de stock aident à régulariser les quantités. |
| 14 | Inventaires | Inventaire hebdomadaire et contrôles supplémentaires si besoin |
| 15 | Corrections de stock | Tous les employés peuvent corriger ; historique complet et motif conservés |
| 16 | Dépenses | Dépenses catégorisées |
| 17 | Annulation de vente | Traçable avec motif ; l'opération reste dans l'historique ; stock corrigé si nécessaire |
| 18 | Consultation des opérations | Un employé consulte ses propres ventes, dépenses et corrections de stock ; la supervision des opérations de l'équipe dépend du rôle |
| 19 | Responsable d'activité | Pouvoirs étendus sur son activité, peut créer et désactiver les comptes de son équipe, sans accès aux autres activités |
| 20 | Saisie des dépenses | Tous les employés peuvent enregistrer une dépense ; elle est comptée dès sa saisie, et toute correction ou annulation est traçable |
| 21 | Suivi des employés | Le gérant voit les opérations, le nombre de ventes et la dernière opération par employé |
| 22 | Catalogue | Tous les employés peuvent créer des produits et prestations, actifs immédiatement sans approbation préalable |
| 23 | Prix | Tous les employés peuvent modifier les prix ; chaque changement est historisé |
| 24 | Entrée de stock | Quantité, coût, date et auteur enregistrés |
| 25 | Achats et dépenses | Les achats qui alimentent le stock sont séparés des autres dépenses (pas de double comptage) |
| 26 | Tableau de bord | Ventes, finances, alertes de stock, produits sans ventes, activités sans ventes enregistrées |
| 27 | Base de données | SQLite |
| 28 | Mode hors ligne | Reporté après la V1 |
| 29 | Sauvegardes | Automatiques et quotidiennes ; restauration vérifiée |
| 30 | Tests | Tests manuels structurés et scénarios métier ; automatisation en priorité des permissions, calculs financiers et mouvements de stock si le temps le permet |
| 31 | Livraison | Version opérationnelle pour les trois activités au 3 novembre 2026 |
| 32 | Produits stockés | Boutique et coiffure ont toutes deux des produits revendus qui sont suivis en stock |
| 33 | Vente groupée | Une vente groupée peut mélanger des produits et des prestations |

---

## 5. Règles de calcul et de traçabilité

### 5.1 Ventes de produits

Chaque ligne de vente conserve la quantité, le prix de vente réellement appliqué et le coût unitaire retenu au moment de la transaction. Une modification ultérieure du prix catalogue ne recalcule jamais les ventes passées.

> Marge estimée d'une ligne = (prix de vente appliqué − coût unitaire retenu) × quantité vendue

Le coût unitaire provient du coût moyen d'achat et est figé sur la ligne de vente.

### 5.2 Coût moyen des produits

Après une nouvelle entrée, si le stock avant l'entrée est positif et sa valeur connue :

> Coût moyen = (valeur du stock avant l'entrée + coût total de l'entrée) / (quantité en stock avant l'entrée + quantité entrée)

Si une entrée fait repasser le stock au-dessus de zéro, le coût moyen repart du coût unitaire de cette entrée, sans inclure la quantité négative dans le calcul. Tant que le stock reste nul ou négatif, la marge est signalée « indisponible ou peu fiable ». Les vérifications de stock fréquentes aident à régulariser les quantités.

Les quantités et les coûts utilisent des types numériques adaptés, notamment `Decimal` pour tous les montants financiers.

### 5.3 Coiffure et dépenses

La V1 n'impose pas de coût par coupe ou prestation. Elle affiche les recettes de la coiffure, les dépenses catégorisées enregistrées et un solde estimatif après dépenses déclarées. Ce solde n'est pas un bénéfice net si des charges ne sont pas enregistrées. Les achats de stock sont exclus des dépenses générales lorsqu'ils sont déjà pris en compte dans le coût des produits vendus.

### 5.4 Vente groupée

Une vente groupée conserve au minimum son auteur, son horodatage, les articles, les quantités, les prix appliqués et son montant. Elle représente une saisie regroupée, pas la preuve que chaque transaction individuelle a été enregistrée.

### 5.5 Stock et inventaire

- Le stock n'est modifié que par un service central qui crée en même temps un mouvement traçable.
- Chaque correction exige un motif ; aucune opération validée n'est supprimée silencieusement.
- Une vente au-delà du stock est enregistrée avec avertissement, et la valeur négative est conservée.
- Pour l'inventaire : soit les mouvements sur les produits comptés sont suspendus pendant le comptage, soit les mouvements intervenus depuis le début du comptage sont intégrés au calcul de l'écart. Cette règle est implémentée explicitement.

---

## 6. Rôles et permissions

| Action | Employé | Responsable d'activité | Gérant global |
|---|---|---|---|
| Enregistrer une vente | Oui, sa propre vente | Oui | Oui |
| Consulter les ventes | Ses propres ventes | Toutes celles de son activité | Toutes les activités |
| Créer produit/prestation | Oui | Oui | Oui |
| Modifier un prix | Oui, historisé | Oui, historisé | Oui, historisé |
| Corriger le stock | Oui, motif + historique | Oui, motif + historique | Oui, motif + historique |
| Enregistrer une dépense | Oui, catégorie + auteur | Oui | Oui |
| Consulter le tableau de bord | Limité à ses opérations | Son activité | Toutes les activités |
| Gérer les utilisateurs | Non | Dans son activité (voir A2) | Oui |
| Consulter l'historique global | Non | Son activité | Toutes les activités |

L'accès est toujours vérifié **côté serveur**. Un responsable ne doit pas pouvoir consulter les données d'une autre activité en modifiant une URL.

---

## 7. Architecture technique

Une seule application Django, organisée en modules métier, plutôt que trois applications indépendantes.

### 7.1 Structure du projet

```
jed/
├── config/                 # Configuration Django
├── apps/
│   ├── accounts/           # Utilisateurs, rôles, permissions
│   ├── activities/         # Restaurant-bar, coiffure, boutique
│   ├── catalog/            # Produits, services, unités, prix
│   ├── inventory/          # Stocks, approvisionnements, corrections
│   ├── sales/              # Ventes et lignes de vente
│   ├── expenses/           # Dépenses et catégories
│   ├── analytics/          # Indicateurs et tableaux de bord
│   └── audit/              # Historique des opérations sensibles
├── templates/
├── static/
├── manage.py
└── requirements.txt
```

Cette structure est une cible. Si huit applications Django compliquent le démarrage, certains modules peuvent être regroupés, à condition de séparer les responsabilités.

### 7.2 Entités principales

| Entité | Rôle |
|---|---|
| User | Compte utilisateur et authentification |
| Activity | Activité commerciale |
| ActivityMembership | Activité accessible à un utilisateur et rôle dans cette activité |
| Product | Produit commercialisé, unité de référence, coût d'achat moyen |
| Service | Prestation vendue, sans consommation automatique de stock |
| StockMovement | Entrée, sortie, correction, perte ou autre mouvement de stock |
| Sale | En-tête de vente : auteur, date, activité, statut |
| SaleLine | Produit ou service vendu, quantité, prix réellement appliqué, coût unitaire retenu |
| Expense | Dépense : catégorie, montant, auteur, statut |
| AuditLog | Historique des opérations sensibles et de leurs auteurs |

Les champs exacts sont fixés avant de générer les modèles définitifs.

### 7.3 Choix techniques

| Élément | Choix | Implication |
|---|---|---|
| Backend | Django | Templates Django et logique serveur, sans SPA ni API si inutile |
| Base de données | SQLite | Limites en écritures concurrentes : transactions courtes, écritures de stock centralisées, test avec plusieurs utilisateurs actifs |
| Interface | Web responsive | Utilisable sur téléphone et PC |
| Mode hors ligne | Reporté | Aucune saisie hors ligne en V1 |
| Déploiement | Hébergement web | HTTPS, secrets en variables d'environnement, DEBUG désactivé, hôtes autorisés, fichiers statiques |
| Sauvegarde | Automatique quotidienne | Copie hors du serveur principal ; restauration testée |
| Tests | Manuels structurés | Automatiser en priorité permissions, calculs financiers, mouvements de stock |

Si les tests montrent que SQLite ne répond pas au besoin, le passage à PostgreSQL est une décision explicite, jamais un changement silencieux.

### 7.4 Quatre règles techniques non négociables

1. **Permissions côté serveur.** Masquer un bouton ne suffit pas ; les requêtes sont filtrées par activité.
2. **Cohérence financière et stock.** Une vente, ses lignes et ses mouvements de stock sont enregistrés dans une seule transaction de base de données. Si une étape échoue, tout est annulé.
3. **Prix historiques figés.** Modifier le prix actuel ne modifie pas les ventes passées.
4. **Corrections traçables.** Une vente annulée, une dépense corrigée ou un stock ajusté ne disparaît jamais silencieusement de l'historique.

---

## 8. Ordre de développement

Les phases respectent les dépendances : développer le tableau de bord avant de fiabiliser les ventes produirait des indicateurs faux.

### Phase 1 — Fondations et sécurité
- Créer le projet Django, configurer SQLite.
- Paramètres de développement et de production séparés.
- Authentification, rôles et périmètres d'accès.
- Création des activités.
- Modèles communs et migrations.

**Validation** : le gérant global accède à toutes les activités ; un responsable n'accède qu'à son périmètre.

### Phase 2 — Catalogue et stock
- Produits et services ; unités de référence et conversions d'emballage.
- Approvisionnements (quantité, coût, date, auteur) ; coût moyen d'achat.
- Corrections, pertes et écarts d'inventaire.
- Mouvements avec motif et auteur.

**Validation** : après plusieurs approvisionnements, ventes et corrections, le stock calculé correspond aux mouvements enregistrés.

### Phase 3 — Ventes
- Vente individuelle et vente groupée (plusieurs produits ou services).
- Prix réellement appliqué conservé par ligne ; auteur et heure enregistrés.
- Diminution du stock des produits concernés.
- Annulation avec justification et historique ; correction du stock si nécessaire.

**Validation** : une vente groupée produit les bons montants et les bons mouvements de stock.

### Phase 4 — Dépenses et indicateurs financiers
- Dépenses par catégorie ; correction et annulation avec justification.
- Achats de stock enregistrés séparément.
- Calcul du chiffre d'affaires et des marges estimées des produits.
- Recettes et dépenses des activités de service.

**Règle** : un résultat calculé à partir de données incomplètes n'est jamais présenté comme un bénéfice comptable certifié.

### Phase 5 — Tableaux de bord

Le tableau de bord du gérant global présente :
- le chiffre d'affaires par activité ;
- le nombre de ventes et leur évolution ;
- les produits les plus vendus ;
- les marges estimées disponibles ;
- les alertes de stock ;
- les produits sans ventes récentes ;
- la dernière opération enregistrée par employé ;
- les activités sans vente enregistrée depuis 8 h (formulé comme une absence de ventes enregistrées).

Le responsable d'activité ne voit que son périmètre. Les comparaisons entre périodes, les périodes personnalisées et l'inventaire hebdomadaire complet (P1) sont ajoutés si les flux essentiels sont stables.

### Phase 6 — Tests, sauvegardes et mise en production
- Tester les permissions de chaque rôle.
- Vérifier les calculs de ventes et de dépenses.
- Tester ventes groupées, annulations, mouvements de stock et stock négatif.
- Vérifier corrections et historique.
- Automatiser les sauvegardes quotidiennes ; **effectuer une vraie restauration** sur une copie de test.
- Désactiver le mode débogage ; configurer secrets, hôtes autorisés, HTTPS et fichiers statiques.
- Vérifier le fonctionnement depuis un autre appareil.
- Formation courte et guide utilisateur.

Une sauvegarde n'est fiable que lorsque sa restauration a été testée.

---

## 9. Calendrier intensif

| Date | Travail prioritaire | Livrable attendu |
|---|---|---|
| 26 octobre | Initialisation, architecture, modèles, authentification | Projet démarré, migrations fonctionnelles |
| 27 octobre | Activités, rôles, permissions, catalogue | Comptes et catalogue utilisables |
| 28 octobre | Approvisionnements et mouvements de stock | Stock calculé à partir des mouvements |
| 29 octobre | Ventes individuelles et groupées | Cycle de vente fonctionnel |
| 30 octobre | Dépenses, annulations, historique | Opérations traçables |
| 31 octobre | Calculs financiers, tableaux de bord essentiels | Indicateurs cohérents |
| 1er novembre | Tests fonctionnels, corrections, sauvegardes | Scénarios métier validés |
| 2 novembre | Déploiement, sécurisation, tests en ligne | Application accessible en production |
| 3 novembre | Réserve pour anomalies critiques, validation finale | Version livrable |

Ce calendrier est un objectif agressif, pas une garantie. La règle de repli de la section 1 s'applique.

---

## 10. Scénarios de recette

| Scénario | Résultat attendu |
|---|---|
| Un employé tente d'accéder à une autre activité (y compris par l'URL) | Accès refusé |
| Un employé crée un produit | Produit utilisable immédiatement |
| Entrée de stock | Quantité, coût, date et auteur conservés ; stock augmenté ; coût moyen recalculé |
| Vente simple d'un produit | Stock diminué ; prix et coût de la ligne conservés ; chiffre d'affaires augmenté |
| Vente d'une prestation | Aucun mouvement de stock |
| Vente groupée de trois produits | Chaque ligne conserve prix, quantité et montant ; total, auteur et horodatage cohérents |
| Vente au-delà du stock | Vente enregistrée ; stock négatif ; avertissement visible ; marge signalée peu fiable |
| Correction de stock | Motif, auteur, heure et écart consultables ; historique antérieur intact |
| Annulation de vente | Vente exclue des totaux actifs ; historique conservé ; stock rétabli par opération inverse |
| Correction de dépense | Correction visible et justifiée |
| Modification du prix | Nouvelles ventes au nouveau prix ; anciennes ventes inchangées |
| Inventaire | Validation impossible deux fois ; mouvements pendant le comptage sans effet sur l'écart |
| Dépenses | Catégorisées ; achats de stock non comptés deux fois |
| Tableau de bord | Totaux = ventes non annulées de la période sélectionnée |
| Sauvegarde restaurée | Données sauvegardées effectivement récupérées |

---

## 11. Hébergement et budget

Le budget de **200 000 FCFA** couvre tout le projet. Une enveloppe distincte est réservée pour :
- le domaine ;
- douze mois d'hébergement ;
- les sauvegardes externes si elles sont payantes ;
- une marge pour frais de paiement ou de renouvellement.

Critères de choix de l'hébergeur (le tarif d'entrée seul ne suffit pas) :
- exécution d'une application Django ;
- persistance du fichier SQLite après redémarrage ou redéploiement ;
- limites de stockage ;
- sauvegarde de la base hors du serveur principal ;
- prise en charge de HTTPS ;
- conditions de renouvellement et moyens de paiement acceptés depuis le Cameroun.

---

## 12. Décisions métier tranchées avant le codage

Les questions **A1 à A10 sont désormais tranchées**. Les réponses aux questions métier A2 à A8 ont été confirmées le 26 octobre 2026 et sont intégrées dans les décisions ci-dessus :

| Réf. | Décision validée |
|---|---|
| A2 | Le responsable d'activité peut créer et désactiver les comptes de son équipe. |
| A3 | L'employé consulte ses propres ventes, dépenses et corrections de stock. |
| A4 | Au retour à un stock positif, le coût moyen repart du coût unitaire de la nouvelle entrée; le stock négatif n'est pas inclus. La marge est peu fiable tant que le stock est nul ou négatif. |
| A5 | La dépense est comptée à la saisie; corrections et annulations sont traçables. |
| A6 | Boutique et coiffure ont des produits revendus suivis en stock. |
| A7 | Une vente groupée peut mélanger produits et prestations. |
| A8 | Produits et prix créés par les employés sont actifs immédiatement, sans approbation préalable. |

---

## 13. Conventions de développement

- Toute opération financière ou de stock est exécutée côté serveur, dans une transaction lorsque plusieurs enregistrements sont liés.
- Aucun stock n'est modifié hors du service central de mouvements.
- Les opérations validées ne sont pas supprimées ; les erreurs sont rectifiées par annulation ou mouvement inverse traçable.
- Les permissions sont contrôlées dans les vues et services ; les requêtes sont filtrées par activité.
- Aucune fonctionnalité non prévue avant la fin des parcours métier essentiels.
- Commits Git courts et réguliers ; secrets, fichiers `.env` et sauvegardes exclus du dépôt.
- La sauvegarde est restaurée au moins une fois pendant la recette avant la livraison.
- Une fonctionnalité est terminée quand son comportement métier est vérifié, pas quand son interface s'affiche.

---

## 14. Prochaine action

Convertir ce plan en une liste de tâches de développement ordonnée. Pour chaque tâche :

1. fichiers à créer ou modifier ;
2. modèles concernés ;
3. règles métier à respecter ;
4. critères de validation ;
5. commit Git à réaliser après validation.

Tenir un journal de progression dans le dépôt (`PROGRESS.md`) : tâche terminée, tâche en cours, problèmes connus, prochaine action.

**Ordre de départ** : initialiser le dépôt Git, créer le projet Django, configurer SQLite, mettre en place utilisateurs et activités, puis valider les permissions avant de développer le catalogue.
