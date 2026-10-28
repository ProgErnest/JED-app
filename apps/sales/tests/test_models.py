"""
Tests persistants JED-07 — module des ventes.

Couvre :
- ``create_sale`` (service central) : snapshots prix/coût, mouvements stock,
  rollback transactionnel, services (coût = 0), stock négatif.
- ``SaleLineForm`` / ``SaleLineFormSet`` : validation, lignes vides,
  produits+services simultanés, quantité.
- Vues (``SaleListView``, ``SaleCreateView``, ``SaleDetailView``) : flux web,
  permissions par activité (403 / 302), formulaire vide.
- ``SaleLine.margin`` (calcul de marge).
"""
