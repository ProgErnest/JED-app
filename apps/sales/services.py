"""Service central des ventes (JED-07).

Toute création de ticket de caisse passe par ``create_sale``, dans une
transaction atomique. Le prix de vente et le coût sont **snapshot** dans les
lignes au moment de la vente, et les sorties de stock sont enregistrées via le
service central ``record_stock_movement`` (JED-05).
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.catalog.models import Product, Service
from apps.inventory.models import StockMovement
from apps.inventory.services import record_stock_movement

from .models import Sale, SaleLine


def create_sale(activity, user, lines_data):
    """Crée un ticket de caisse et ses mouvements de stock atomiquement.

    Paramètres
    ----------
    activity : activities.Activity
    user : User
        Auteur du ticket.
    lines_data : list[dict]
        Chaque dict possède une clé ``item`` (Product ou Service) et une clé
        ``quantity`` (int positif).

    Règles métier
    -------------
    - Le prix de vente appliqué est celui en vigueur au moment de la vente
      (snapshot dans ``SaleLine.unit_price``) — décision A10.
    - Un ``Product`` déclenche une sortie de stock (``EXIT``). Un ``Service``
      n'a aucune sortie de stock (coût = 0).
    - Une panne sur n'importe quelle ligne (ou mouvement de stock) annule
      l'ensemble du ticket (rollback transactionnel).
    - Le stock peut devenir négatif : la marge est alors signalée comme
      peu fiable (décision A4).

    Retourne le ``Sale`` enregistré.
    """
    if not lines_data:
        raise ValueError("Un ticket de caisse doit contenir au moins une ligne.")

    with transaction.atomic():
        sale = Sale.objects.create(activity=activity, user=user, total=Decimal(0))
        total = Decimal(0)

        for data in lines_data:
            item = data["item"]
            quantity = int(data["quantity"])
            if quantity <= 0:
                raise ValueError("La quantité d'une ligne doit être positive.")

            if isinstance(item, Product):
                if item.activity_id != activity.pk:
                    raise ValueError("Le produit doit appartenir à l'activité de la vente.")
                unit_price = item.price  # snapshot prix de vente
                cost = item.average_cost  # snapshot coût moyen
                # Sortie de stock centralisée (jamais directement).
                record_stock_movement(
                    product=item,
                    movement_type=StockMovement.MovementType.EXIT,
                    quantity=quantity,
                    user=user,
                    reason="Vente",
                    activity=activity,
                )
                product = item
                service = None
                margin_reliable = item.stock_quantity > 0
            elif isinstance(item, Service):
                if item.activity_id != activity.pk:
                    raise ValueError("La prestation doit appartenir à l'activité de la vente.")
                unit_price = item.price
                cost = Decimal(0)  # prestation : pas de stock, pas de coût
                margin_reliable = True
                product = None
                service = item
            else:
                raise ValueError(
                    "L'élément d'une ligne doit être un Product ou un Service."
                )

            line_total = unit_price * quantity
            SaleLine.objects.create(
                sale=sale,
                product=product,
                service=service,
                quantity=quantity,
                unit_price=unit_price,
                cost=cost,
                margin_reliable=margin_reliable,
                total=line_total,
            )
            total += line_total

        sale.total = total
        sale.save(update_fields=["total"])
        return sale
