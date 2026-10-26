"""Service central des mouvements de stock (JED-05).

Toute modification de stock passe par ``record_stock_movement``, dans une
transaction atomique. Aucun stock n'est modifié hors de ce service.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import StockMovement


def record_stock_movement(product, movement_type, quantity, unit_cost=None, user=None, reason="", activity=None):
    """Enregistre un mouvement de stock et met à jour le produit atomiquement.

    Paramètres
    ----------
    product : catalog.Product
        Produit concerné.
    movement_type : str
        L'une des valeurs de ``StockMovement.MovementType``.
    quantity : int
        Quantité saisie (positive). Le signe est déterminé par le type de
        mouvement : positif pour une entrée, négatif pour une sortie, signé
        pour une correction.
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
    if not user:
        raise ValidationError("L'auteur est obligatoire.")
    if activity is None:
        activity = product.activity

    # Quantité signée selon le type de mouvement
    if movement_type == StockMovement.MovementType.ENTRY:
        signed_qty = abs(quantity)  # entrée : toujours positif
    elif movement_type == StockMovement.MovementType.EXIT:
        signed_qty = -abs(quantity)  # sortie : toujours négatif
    else:  # CORRECTION
        signed_qty = quantity  # signé tel quel

    stock_avant = product.stock_quantity

    with transaction.atomic():
        if movement_type == StockMovement.MovementType.ENTRY:
            if unit_cost is None:
                raise ValidationError("Le coût unitaire est obligatoire pour une entrée.")
            nouveau_stock = stock_avant + signed_qty

            if stock_avant > 0:
                # Coût moyen pondéré
                total_value = stock_avant * product.average_cost + signed_qty * unit_cost
                product.average_cost = total_value / nouveau_stock
            elif stock_avant == 0:
                product.average_cost = unit_cost
            else:  # stock_avant < 0
                # Règle A4 : si l'entrée fait repasser le stock au-dessus de zéro,
                # le coût moyen repart du coût unitaire de cette entrée.
                if nouveau_stock > 0:
                    product.average_cost = unit_cost
                # sinon : reste <= 0, average_cost inchangé (non fiable)

            product.stock_quantity = nouveau_stock

        elif movement_type == StockMovement.MovementType.EXIT:
            product.stock_quantity += signed_qty  # signé négatif

        elif movement_type == StockMovement.MovementType.CORRECTION:
            product.stock_quantity += signed_qty

        product.save()

        StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity=signed_qty,
            unit_cost=unit_cost if movement_type == StockMovement.MovementType.ENTRY else None,
            user=user,
            activity=activity,
            reason=reason,
        )

    return product
