"""Service central des ventes (JED-07).

Toute création de ticket de caisse passe par ``create_sale``, dans une
transaction atomique. Le prix de vente et le coût sont **snapshot** dans les
lignes au moment de la vente, et les sorties de stock sont enregistrées via le
service central ``record_stock_movement`` (JED-05).
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.accounts.permissions import user_has_activity_access, user_is_employee_in_activity
from apps.catalog.models import Product, Service
from apps.inventory import services as inventory_services
from apps.inventory.models import StockMovement

from .models import Sale, SaleCancellation, SaleLine


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
                inventory_services.record_stock_movement(
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


def cancel_sale(sale, user, reason):
    """Annule un ticket une seule fois, en restaurant le stock atomiquement."""
    reason = reason.strip() if isinstance(reason, str) else ""
    if not reason:
        raise ValidationError("Le motif d'annulation est obligatoire.")
    if not user or not getattr(user, "is_authenticated", False):
        raise ValidationError("L'auteur de l'annulation est obligatoire.")
    if not user_has_activity_access(user, sale.activity):
        raise ValidationError("Accès non autorisé à cette activité.")
    if user_is_employee_in_activity(user, sale.activity) and sale.user_id != user.pk:
        raise ValidationError("Un employé ne peut annuler que ses propres ventes.")

    with transaction.atomic():
        locked_sale = Sale.objects.select_for_update().select_related("activity").get(pk=sale.pk)
        if SaleCancellation.objects.filter(sale=locked_sale).exists():
            return SaleCancellation.objects.get(sale=locked_sale)

        cancellation = SaleCancellation.objects.create(
            sale=locked_sale,
            user=user,
            reason=reason,
        )
        lines = locked_sale.lines.select_related("product")
        for line in lines:
            if line.product_id is None:
                continue
            inventory_services.record_stock_movement(
                product=line.product,
                movement_type=StockMovement.MovementType.CORRECTION,
                quantity=line.quantity,
                user=user,
                reason=f"Annulation ticket #{locked_sale.pk}: {reason}",
                activity=locked_sale.activity,
            )
        return cancellation
