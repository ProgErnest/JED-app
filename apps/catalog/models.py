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
    stock_quantity = models.IntegerField("quantité en stock", default=0, help_text="Peut être négatif en cas d'erreur de saisie.")
    average_cost = models.DecimalField("coût moyen", max_digits=10, decimal_places=2, default=0, help_text="Coût moyen pondéré d'achat. Non fiable si le stock est nul ou négatif.")
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
        previous_price = None
        update_fields = kwargs.get("update_fields")
        price_will_be_saved = update_fields is None or "price" in update_fields
        if self.pk is not None:
            try:
                previous_price = Product.objects.only("price").get(pk=self.pk).price
            except Product.DoesNotExist:
                pass

        super().save(*args, **kwargs)
        content_type = ContentType.objects.get_for_model(Product)
        current_history = PriceHistory.objects.filter(
            content_type=content_type,
            object_id=self.pk,
            ends_at__isnull=True,
        ).first()

        if current_history is None:
            PriceHistory.objects.create(
                content_type=content_type,
                object_id=self.pk,
                price=self.price,
                starts_at=self.updated_at,
                created_by=getattr(self, "_current_user", None),
            )
        elif (
            price_will_be_saved
            and previous_price is not None
            and previous_price != self.price
        ):
            now = timezone.now()
            current_history.ends_at = now
            current_history.save(update_fields=["ends_at"])
            PriceHistory.objects.create(
                content_type=content_type,
                object_id=self.pk,
                price=self.price,
                starts_at=now,
                created_by=getattr(self, "_current_user", None),
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
        previous_price = None
        update_fields = kwargs.get("update_fields")
        price_will_be_saved = update_fields is None or "price" in update_fields
        if self.pk is not None:
            try:
                previous_price = Service.objects.only("price").get(pk=self.pk).price
            except Service.DoesNotExist:
                pass

        super().save(*args, **kwargs)
        content_type = ContentType.objects.get_for_model(Service)
        current_history = PriceHistory.objects.filter(
            content_type=content_type,
            object_id=self.pk,
            ends_at__isnull=True,
        ).first()

        if current_history is None:
            PriceHistory.objects.create(
                content_type=content_type,
                object_id=self.pk,
                price=self.price,
                starts_at=self.updated_at,
                created_by=getattr(self, "_current_user", None),
            )
        elif (
            price_will_be_saved
            and previous_price is not None
            and previous_price != self.price
        ):
            now = timezone.now()
            current_history.ends_at = now
            current_history.save(update_fields=["ends_at"])
            PriceHistory.objects.create(
                content_type=content_type,
                object_id=self.pk,
                price=self.price,
                starts_at=now,
                created_by=getattr(self, "_current_user", None),
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

