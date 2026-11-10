"""Modèles des ventes (JED-07).

Un ticket de caisse (``Sale``) contient plusieurs lignes (``SaleLine``). Chaque
ligne référence soit un ``Product`` (décrémentant le stock, coût = coût moyen
snapshot), soit un ``Service`` (aucune sortie de stock, coût = 0). Le prix de
vente et le coût sont **figés** dans la ligne au moment de la vente : une
modification ultérieure du prix du catalogue n'impacte pas les ventes passées.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


class Sale(models.Model):
    """Ticket de caisse : un ensemble de lignes de vente."""

    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.CASCADE,
        related_name="sales",
        verbose_name="activité",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name="auteur",
    )
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)
    total = models.DecimalField(
        "total", max_digits=10, decimal_places=2, default=Decimal(0)
    )

    class Meta:
        verbose_name = "ticket de caisse"
        verbose_name_plural = "tickets de caisse"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["activity", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Ticket #{self.pk:d} — {self.activity.name} — {self.total}"

    @property
    def is_canceled(self) -> bool:
        """Indique si un événement d'annulation existe pour ce ticket."""
        if hasattr(self, "_is_canceled"):
            return self._is_canceled
        if "cancellation" in self._state.fields_cache:
            return self._state.fields_cache["cancellation"] is not None
        return SaleCancellation.objects.filter(sale_id=self.pk).exists()


class SaleLine(models.Model):
    """Ligne de ticket : un produit ou un service vendu."""

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name="ticket",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_lines",
        verbose_name="produit",
    )
    service = models.ForeignKey(
        "catalog.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_lines",
        verbose_name="prestation",
    )
    category_id_snapshot = models.PositiveBigIntegerField(
        "identifiant de rubrique (snapshot)", null=True, blank=True
    )
    category_name_snapshot = models.CharField(
        "rubrique (snapshot)", max_length=100, blank=True
    )
    quantity = models.PositiveIntegerField("quantité", default=1)
    # Snapshots au moment de la vente (immuables) — décision A10.
    unit_price = models.DecimalField(
        "prix de vente (snapshot)", max_digits=10, decimal_places=2, default=Decimal(0)
    )
    cost = models.DecimalField(
        "coût (snapshot)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text="Coût moyen connu au moment de la vente; vide si le coût est inconnu.",
    )
    margin_reliable = models.BooleanField(
        "marge fiable",
        default=False,
        help_text="La marge est non fiable si le stock était nul ou négatif; faux pour les ventes historiques non vérifiables.",
    )
    total = models.DecimalField(
        "total ligne", max_digits=10, decimal_places=2, default=Decimal(0)
    )

    class Meta:
        verbose_name = "ligne de ticket"
        verbose_name_plural = "lignes de ticket"
        ordering = ["sale__created_at", "id"]

    def __str__(self) -> str:
        return f"{self.item_display} × {self.quantity}"

    @property
    def item(self):
        """L'élément vendu (Product ou Service)."""
        return self.product or self.service

    @property
    def item_display(self) -> str:
        item = self.item
        return str(item) if item else "—"

    @property
    def margin(self) -> Decimal | None:
        """Marge brute de la ligne, ou None si son coût est inconnu."""
        if self.cost is None:
            return None
        return (self.unit_price - self.cost) * self.quantity

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        super().clean()
        if not (self.product or self.service):
            raise ValidationError(
                "Une ligne de vente doit référencer un produit ou un service."
            )
        if self.product and self.service:
            raise ValidationError(
                "Une ligne ne peut référencer qu'un produit ou un service, pas les deux."
            )
        if self.quantity <= 0:
            raise ValidationError("La quantité doit être positive.")
        if self.unit_price < 0:
            raise ValidationError("Le prix de vente ne peut être négatif.")


class SaleCancellation(models.Model):
    """Événement d'annulation immuable associé à un ticket de caisse."""

    sale = models.OneToOneField(
        Sale,
        on_delete=models.PROTECT,
        related_name="cancellation",
        verbose_name="ticket annulé",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="sale_cancellations",
        verbose_name="auteur de l'annulation",
    )
    reason = models.TextField("motif")
    created_at = models.DateTimeField("annulé le", auto_now_add=True)

    class Meta:
        verbose_name = "annulation de vente"
        verbose_name_plural = "annulations de vente"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Annulation du ticket #{self.sale_id}"
