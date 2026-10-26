"""Modèle ``Activity`` — activités métier du projet JED (JED-02)."""

from __future__ import annotations

from django.db import models


class Activity(models.Model):
    """Une activité commerciale gérée par JED (ex: restaurant-bar, coiffure, boutique).

    Les données de vente, stock et dépenses sont ensuite filtrées par activité
    afin d'isoler le périmètre de chaque utilisateur selon son rôle.
    """

    name = models.CharField("nom", max_length=100, unique=True)
    slug = models.SlugField("slug", max_length=100, unique=True)
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        verbose_name = "activité"
        verbose_name_plural = "activités"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
