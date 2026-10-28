"""Modèle ``StockMovement`` — mouvements de stock centralisés (JED-05).

Tous les mouvements de stock (entrées, sorties liées aux ventes, corrections)
passent par ce modèle et par le service central ``record_stock_movement``.
Aucun stock n'est modifié hors de ce service.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models


class StockMovement(models.Model):
    """Un mouvement de stock sur un produit.

    ``quantity`` est positive pour une entrée, négative pour une sortie, et
    peut être l'un ou l'autre pour une correction.
    """

    class MovementType(models.TextChoices):
        ENTRY = "ENTRY", "Entrée (approvisionnement)"
        EXIT = "EXIT", "Sortie (vente)"
        CORRECTION = "CORRECTION", "Correction / ajustement"

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="produit",
    )
    movement_type = models.CharField("type de mouvement", max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField("quantité", help_text="Positif = entrée, négatif = sortie.")
    unit_cost = models.DecimalField(
        "coût unitaire",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Coût unitaire d'achat pour une entrée.",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="auteur",
    )
    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="activité",
    )
    reason = models.TextField("motif", blank=True, help_text="Obligatoire pour une correction.")
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "mouvement de stock"
        verbose_name_plural = "mouvements de stock"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["activity", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.quantity} — {self.get_movement_type_display()}"
