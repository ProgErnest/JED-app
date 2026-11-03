"""Service central des mouvements de stock (JED-05).

Toute modification de stock passe par ``record_stock_movement``, dans une
transaction atomique. Aucun stock n'est modifié hors de ce service.
"""

from __future__ import annotations

from decimal import Decimal

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import StockMovement


def record_stock_movement(
    product,
    movement_type,
    quantity=None,
    unit_cost=None,
    user=None,
    reason="",
    activity=None,
    counted_quantity=None,
):
    """Enregistre un mouvement de stock et met à jour le produit atomiquement.

    Paramètres
    ----------
    product : catalog.Product
        Produit concerné.
    movement_type : str
        L'une des valeurs de ``StockMovement.MovementType``.
    quantity : int, optional
        Quantité positive d'entrée/sortie, ou écart signé pour les corrections
        internes. À omettre lorsqu'un comptage physique est fourni.
    counted_quantity : int, optional
        Quantité réelle observée. Pour une correction, le service calcule
        l'écart depuis le stock courant après verrouillage du produit et la
        conserve dans l'historique du mouvement.
    unit_cost : Decimal, optional
        Coût unitaire d'achat, obligatoire pour une entrée.
    user : User
        Auteur du mouvement (obligatoire).
    reason : str
        Motif du mouvement (obligatoire pour une correction).
    activity : activities.Activity, optional
        Activité concernée (déduite du produit si omise).

    Règles métier (A4) :
    - Lorsqu'une entrée ramène le stock au-dessus de zéro depuis un stock
      négatif, le coût moyen repart du coût unitaire de cette entrée, sans
      inclure la quantité négative.
    - Tant que le stock reste nul ou négatif, le coût moyen est considéré
      comme non fiable.

    Retourne le produit mis à jour.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise ValidationError("L'auteur est obligatoire.")
    if activity is None:
        activity = product.activity
    if activity.pk != product.activity_id:
        raise ValidationError("L'activité du mouvement doit correspondre au produit.")

    movement_types = StockMovement.MovementType
    if movement_type not in movement_types.values:
        raise ValidationError("Type de mouvement invalide.")

    uses_counted_quantity = (
        movement_type == movement_types.CORRECTION and counted_quantity is not None
    )
    if uses_counted_quantity:
        if (
            not isinstance(counted_quantity, int)
            or isinstance(counted_quantity, bool)
            or counted_quantity < 0
        ):
            raise ValidationError("La quantité comptée doit être un entier positif ou nul.")
        if quantity is not None:
            raise ValidationError("Saisissez soit une quantité comptée, soit un écart.")
    elif not isinstance(quantity, int) or isinstance(quantity, bool):
        raise ValidationError("La quantité doit être un nombre entier.")
    if movement_type == movement_types.ENTRY:
        if quantity <= 0:
            raise ValidationError("La quantité d'entrée doit être positive.")
        if unit_cost is None:
            raise ValidationError("Le coût unitaire est obligatoire pour une entrée.")
        if (
            not isinstance(unit_cost, Decimal)
            or not unit_cost.is_finite()
            or unit_cost < 0
        ):
            raise ValidationError("Le coût unitaire doit être un montant positif ou nul.")
    elif unit_cost is not None:
        raise ValidationError("Le coût unitaire ne s'applique qu'aux entrées de stock.")
    if (
        movement_type in (movement_types.EXIT, movement_types.CORRECTION)
        and not uses_counted_quantity
        and quantity == 0
    ):
        raise ValidationError("Le mouvement doit modifier le stock.")
    if movement_type == movement_types.CORRECTION and (
        not isinstance(reason, str) or not reason.strip()
    ):
        raise ValidationError("Le motif est obligatoire pour une correction.")

    with transaction.atomic():
        Product = apps.get_model("catalog", "Product")
        locked_product = Product.objects.select_for_update().get(pk=product.pk)
        if activity.pk != locked_product.activity_id:
            raise ValidationError("L'activité du mouvement doit correspondre au produit.")

        if movement_type == movement_types.ENTRY:
            signed_qty = quantity
            stock_avant = locked_product.stock_quantity
            nouveau_stock = stock_avant + signed_qty

            if stock_avant > 0:
                # Coût moyen pondéré
                total_value = (
                    stock_avant * locked_product.average_cost
                    + signed_qty * unit_cost
                )
                locked_product.average_cost = total_value / nouveau_stock
            elif stock_avant == 0:
                locked_product.average_cost = unit_cost
            else:  # stock_avant < 0
                # Règle A4 : si l'entrée fait repasser le stock au-dessus de zéro,
                # le coût moyen repart du coût unitaire de cette entrée.
                if nouveau_stock > 0:
                    locked_product.average_cost = unit_cost
                # sinon : reste <= 0, average_cost inchangé (non fiable)

            locked_product.stock_quantity = nouveau_stock
        elif movement_type == movement_types.EXIT:
            signed_qty = -abs(quantity)
            locked_product.stock_quantity += signed_qty

        else:  # CORRECTION
            if uses_counted_quantity:
                signed_qty = counted_quantity - locked_product.stock_quantity
                if signed_qty == 0:
                    product.stock_quantity = locked_product.stock_quantity
                    product.average_cost = locked_product.average_cost
                    product.updated_at = locked_product.updated_at
                    product._last_stock_movement = None
                    product._stock_count_unchanged = True
                    return product
                locked_product.stock_quantity = counted_quantity
            else:
                signed_qty = quantity
                locked_product.stock_quantity += signed_qty

        locked_product.save()

        movement = StockMovement.objects.create(
            product=locked_product,
            movement_type=movement_type,
            quantity=signed_qty,
            unit_cost=unit_cost if movement_type == StockMovement.MovementType.ENTRY else None,
            user=user,
            activity=activity,
            reason=reason,
            counted_quantity=counted_quantity if uses_counted_quantity else None,
        )

    product.stock_quantity = locked_product.stock_quantity
    product.average_cost = locked_product.average_cost
    product.updated_at = locked_product.updated_at
    product._last_stock_movement = movement
    product._stock_count_unchanged = False
    return product
