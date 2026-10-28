"""Modèles de gestion des dépenses (JED-09).

Les dépenses sont enregistrées par activité et catégorie, comptabilisées au
moment de leur saisie, et ne peuvent être supprimées silencieusement. Toute
correction ou annulation est tracée dans un journal d'audit.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class ExpenseCategory(models.Model):
    """Catégorie de dépense par activité."""

    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.CASCADE,
        related_name="expense_categories",
        verbose_name="activité",
    )
    name = models.CharField("nom", max_length=120)
    slug = models.SlugField("slug", max_length=120)
    description = models.TextField("description", blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        verbose_name = "catégorie de dépense"
        verbose_name_plural = "catégories de dépense"
        ordering = ["activity__name", "name"]
        unique_together = [("activity", "slug")]

    def __str__(self) -> str:
        return f"{self.name} ({self.activity.name})"


class Expense(models.Model):
    """Dépense générale enregistrée et comptabilisée au moment de la saisie."""

    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.PROTECT,
        related_name="expenses",
        verbose_name="activité",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
        verbose_name="catégorie",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="expenses",
        verbose_name="auteur",
    )
    amount = models.DecimalField("montant", max_digits=12, decimal_places=2)
    description = models.TextField("description", blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)
    is_canceled = models.BooleanField("annulée", default=False)
    canceled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="canceled_expenses",
        verbose_name="annulée par",
    )
    cancellation_reason = models.TextField("motif d'annulation", blank=True)
    canceled_at = models.DateTimeField("annulée le", null=True, blank=True)

    class Meta:
        verbose_name = "dépense"
        verbose_name_plural = "dépenses"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.amount} — {self.category.name}"

    def clean(self) -> None:
        super().clean()
        if self.amount is None or self.amount <= Decimal("0"):
            raise ValidationError({"amount": "Le montant doit être strictement positif."})
        if self.category_id and self.activity_id and self.category.activity_id != self.activity_id:
            raise ValidationError({"category": "La catégorie doit appartenir à l'activité de la dépense."})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                ExpenseAuditLog.objects.create(
                    expense=self,
                    user=self.user,
                    action=ExpenseAuditLog.Action.CREATED,
                    reason="Création de la dépense",
                )

    def cancel(self, user, reason):
        """Annule la dépense de manière traçable."""
        if not user or not getattr(user, "is_authenticated", False):
            raise ValidationError("L'auteur de l'annulation est obligatoire.")
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError("Le motif d'annulation est obligatoire.")
        if self.is_canceled:
            return self

        self.is_canceled = True
        self.canceled_by = user
        self.cancellation_reason = reason
        self.canceled_at = timezone.now()
        self.save(update_fields=[
            "is_canceled",
            "canceled_by",
            "cancellation_reason",
            "canceled_at",
        ])

        ExpenseAuditLog.objects.create(
            expense=self,
            user=user,
            action=ExpenseAuditLog.Action.CANCELLED,
            reason=reason,
        )
        return self


class ExpenseAuditLog(models.Model):
    """Journal d'audit des événements sur une dépense."""

    class Action(models.TextChoices):
        CREATED = "CREATED", "Créée"
        UPDATED = "UPDATED", "Modifiée"
        CANCELLED = "CANCELLED", "Annulée"

    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        verbose_name="dépense",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="expense_audit_logs",
        verbose_name="auteur",
    )
    action = models.CharField("action", max_length=20, choices=Action.choices)
    reason = models.TextField("motif", blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "audit de dépense"
        verbose_name_plural = "audits de dépense"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.expense_id} — {self.action}"
