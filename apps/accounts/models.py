"""Modèle ``ActivityMembership`` — appartenance utilisateur/activité avec rôle (JED-02).

Utilise le modèle ``User`` par défaut de Django. L'appartenance lie un utilisateur
à une activité avec un rôle. Le rôle ``GLOBAL`` (gérant global) n'est lié à aucune
activité particulière et donne une vue sur l'ensemble des activités.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models


class Role(models.TextChoices):
    GLOBAL = "GLOBAL", "Gérant global"
    MANAGER = "MANAGER", "Responsable d'activité"
    EMPLOYEE = "EMPLOYEE", "Employé"


class ActivityMembership(models.Model):
    """Rattachement d'un utilisateur à une activité avec un rôle explicite.

    - ``role = GLOBAL`` : activité nulle (None), accès à toutes les activités.
    - ``role = MANAGER`` / ``EMPLOYEE`` : activité obligatoire, accès limité à celle-ci.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="activity_memberships",
        verbose_name="utilisateur",
    )
    activity = models.ForeignKey(
        "activities.Activity",
        on_delete=models.CASCADE,
        related_name="memberships",
        null=True,
        blank=True,
        verbose_name="activité",
        help_text="Obligatoire sauf pour le rôle Gérant global.",
    )
    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    is_active = models.BooleanField("actif", default=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "appartenance"
        verbose_name_plural = "appartenances"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "activity"],
                name="unique_user_activity_membership",
            ),
        ]
        ordering = ["user__username", "activity__name"]

    def __str__(self) -> str:
        activity_label = self.activity.name if self.activity else "toutes activités"
        return f"{self.user.username} — {activity_label} ({self.get_role_display()})"

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.role == Role.GLOBAL and self.activity is not None:
            raise ValidationError(
                {"activity": "Un gérant global n'est lié à aucune activité particulière."}
            )
        if self.role in (Role.MANAGER, Role.EMPLOYEE) and self.activity is None:
            raise ValidationError(
                {"activity": "Une activité est obligatoire pour un responsable ou un employé."}
            )
