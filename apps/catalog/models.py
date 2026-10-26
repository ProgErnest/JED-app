"""Modèles du catalogue — projet JED (JED-04).

Produits et services rattachés à une activité, avec historique des prix.
Les prix sont stockés en ``Decimal``. Un changement de prix crée une entrée
dans ``PriceHistory`` ; les opérations passées conservent leur prix figé.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class Product(models.Model):
    """Produit physique vendu (ex: boisson, plat, article de boutique)."""

    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="activité",
    )
    name = models.CharField("nom", max_length=150)
    slug = models.SlugField("slug", max_length=150)
    unit = models.CharField("unité", max_length=50, help_text="pièce, kg, litre, bouteille…")
    description = models.TextField("description", blank=True)
    price = models.DecimalField("prix de vente", max_digits=10, decimal_places=2)
    is_active = models.BooleanField("actif", default=True, help_text="Actif immédiatement (A8).")
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "produit"
        verbose_name_plural = "produits"
        unique_together = [("activity", "slug")]
        ordering = ["activity__name", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.activity.name})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            try:
                previous = Product.objects.only("price").get(pk=self.pk)
            except Product.DoesNotExist:
                previous = None
            if previous is not None and previous.price != self.price:
                now = timezone.now()
                PriceHistory.objects.filter(
                    content_type=ContentType.objects.get_for_model(Product),
                    object_id=self.pk,
                    ends_at__isnull=True,
                ).update(ends_at=now)
                PriceHistory.objects.create(
                    content_type=ContentType.objects.get_for_model(Product),
                    object_id=self.pk,
                    price=previous.price,
                    starts_at=previous.updated_at or now,
                    ends_at=now,
                    created_by=getattr(self, "_current_user", None),
                )
        super().save(*args, **kwargs)
        PriceHistory.objects.update_or_create(
            content_type=ContentType.objects.get_for_model(Product),
            object_id=self.pk,
            ends_at__isnull=True,
            defaults={
                "price": self.price,
                "starts_at": self.updated_at,
                "created_by": getattr(self, "_current_user", None),
            },
        )


class Service(models.Model):
    """Prestation de service (ex: coiffure) sans consommation automatique de stock."""

    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name="activité",
    )
    name = models.CharField("nom", max_length=150)
    slug = models.SlugField("slug", max_length=150)
    description = models.TextField("description", blank=True)
    price = models.DecimalField("prix de la prestation", max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField("durée (minutes)", default=30)
    is_active = models.BooleanField("actif", default=True, help_text="Actif immédiatement (A8).")
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "service"
        verbose_name_plural = "services"
        unique_together = [("activity", "slug")]
        ordering = ["activity__name", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.activity.name})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            try:
                previous = Service.objects.only("price").get(pk=self.pk)
            except Service.DoesNotExist:
                previous = None
            if previous is not None and previous.price != self.price:
                now = timezone.now()
                PriceHistory.objects.filter(
                    content_type=ContentType.objects.get_for_model(Service),
                    object_id=self.pk,
                    ends_at__isnull=True,
                ).update(ends_at=now)
                PriceHistory.objects.create(
                    content_type=ContentType.objects.get_for_model(Service),
                    object_id=self.pk,
                    price=previous.price,
                    starts_at=previous.updated_at or now,
                    ends_at=now,
                    created_by=getattr(self, "_current_user", None),
                )
        super().save(*args, **kwargs)
        PriceHistory.objects.update_or_create(
            content_type=ContentType.objects.get_for_model(Service),
            object_id=self.pk,
            ends_at__isnull=True,
            defaults={
                "price": self.price,
                "starts_at": self.updated_at,
                "created_by": getattr(self, "_current_user", None),
            },
        )


class PriceHistory(models.Model):
    """Historique des prix d'un produit ou d'un service.

    Chaque entrée représente une version du prix valide entre ``starts_at`` et
    ``ends_at`` (exclus). L'entrée courante a ``ends_at = NULL``.
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    price = models.DecimalField("prix", max_digits=10, decimal_places=2)
    starts_at = models.DateTimeField("applicable à partir de")
    ends_at = models.DateTimeField("jusqu'à", null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="modifié par",
    )

    class Meta:
        verbose_name = "historique de prix"
        verbose_name_plural = "historiques de prix"
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "-starts_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.item} — {self.price} € dès {self.starts_at:%d/%m/%Y}"

