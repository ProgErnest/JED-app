"""
Utilitaires de permissions centralisés — projet JED (JED-03).

Toute vérification d'accès à une activité est centralisée ici et appelée
côté serveur. Aucun accès implicite à une activité n'est accordé : un
utilisateur doit posséder une appartenance active (ActivityMembership) sur
l'activité visée, sauf le rôle GLOBAL qui voit toutes les activités.
"""

from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from .models import ActivityMembership, Role


def get_user_memberships(user):
    """Retourne les appartenances actives de l'utilisateur.

    Retourne un queryset vide si l'utilisateur n'est pas authentifié.
    """
    if not user or not user.is_authenticated:
        return ActivityMembership.objects.none()
    return ActivityMembership.objects.filter(user=user, is_active=True)


def get_accessible_activities(user):
    """Retourne le queryset des activités accessibles par l'utilisateur.

    - GLOBAL : toutes les activités.
    - MANAGER / EMPLOYEE : uniquement les activités liées à un membership actif.
    """
    from apps.activities.models import Activity

    if not user or not user.is_authenticated:
        return Activity.objects.none()

    memberships = get_user_memberships(user)
    if user.is_superuser or memberships.filter(role=Role.GLOBAL).exists():
        return Activity.objects.all()

    return Activity.objects.filter(
        memberships__user=user, memberships__is_active=True
    ).distinct()


def user_has_activity_access(user, activity) -> bool:
    """Vérifie si l'utilisateur peut accéder à l'activité donnée.

    - GLOBAL : accès à toutes les activités (activity peut être None).
    - MANAGER / EMPLOYEE : accès uniquement à l'activité liée à un membership actif.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True
    # Un GLOBAL a accès à toute activité, quelle qu'elle soit.
    if get_user_memberships(user).filter(role=Role.GLOBAL).exists():
        return True

    if activity is None:
        # Seul un GLOBAL peut accéder à "aucune activité spécifique".
        return False

    membership = get_user_memberships(user).filter(activity=activity).first()
    if membership is None:
        return False

    return membership.role in (Role.MANAGER, Role.EMPLOYEE)


def user_is_global(user) -> bool:
    """Vérifie si l'utilisateur possède un rôle GLOBAL actif."""
    if user and user.is_authenticated and user.is_superuser:
        return True
    return get_user_memberships(user).filter(role=Role.GLOBAL).exists()


def user_can_manage_team(user, activity) -> bool:
    """Vérifie si l'utilisateur peut gérer l'équipe d'une activité (décision A2).

    Autorisé pour GLOBAL (toute activité) et MANAGER sur l'activité concernée.
    """
    if not user or not user.is_authenticated:
        return False
    if activity is None:
        return False
    if user.is_superuser:
        return True
    # Un GLOBAL peut gérer toute activité, quelle qu'elle soit.
    if get_user_memberships(user).filter(role=Role.GLOBAL).exists():
        return True
    membership = get_user_memberships(user).filter(activity=activity).first()
    return membership is not None and membership.role in (Role.GLOBAL, Role.MANAGER)


def user_is_employee_in_activity(user, activity) -> bool:
    """Vérifie si l'utilisateur est employé dans l'activité indiquée."""
    if not user or not user.is_authenticated or user_is_global(user):
        return False
    return get_user_memberships(user).filter(
        activity=activity,
        role=Role.EMPLOYEE,
    ).exists()


# --------------------------------------------------------------------------- #
# Décorateurs pour vues fonction-based
# --------------------------------------------------------------------------- #


def activity_access_required(activity_slug_kwarg="activity_slug"):
    """Décorateur FBV exigeant un accès à l'activité identifiée par le slug d'URL.

    Le paramètre d'URL est attendu sous le nom ``activity_slug_kwarg``
    (défaut : ``activity_slug``). Leve ``PermissionDenied`` (HTTP 403) sinon.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs):
            activity_slug = kwargs.get(activity_slug_kwarg)
            if not activity_slug:
                raise PermissionDenied("Aucune activité spécifiée.")

            from apps.activities.models import Activity

            try:
                activity = Activity.objects.get(slug=activity_slug)
            except Activity.DoesNotExist:
                raise PermissionDenied("Activité introuvable.")

            if not user_has_activity_access(request.user, activity):
                raise PermissionDenied("Accès non autorisé à cette activité.")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def global_or_manager_required(activity_slug_kwarg="activity_slug"):
    """Décorateur FBV exigeant un rôle GLOBAL ou MANAGER sur l'activité."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs):
            activity_slug = kwargs.get(activity_slug_kwarg)
            if not activity_slug:
                raise PermissionDenied("Aucune activité spécifiée.")

            from apps.activities.models import Activity

            try:
                activity = Activity.objects.get(slug=activity_slug)
            except Activity.DoesNotExist:
                raise PermissionDenied("Activité introuvable.")

            if not user_can_manage_team(request.user, activity):
                raise PermissionDenied(
                    "Droits insuffisants pour gérer cette activité."
                )

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


# --------------------------------------------------------------------------- #
# Mixins pour vues class-based
# --------------------------------------------------------------------------- #


class ActivityAccessRequiredMixin:
    """Mixin CBV protégeant l'accès à une activité via son slug d'URL.

    Définir ``activity_slug_kwarg`` (défaut : ``activity_slug``) avec le nom
    du paramètre d'URL contenant le slug de l'activité.
    """

    activity_slug_kwarg = "activity_slug"

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        activity_slug = kwargs.get(self.activity_slug_kwarg)
        if not activity_slug:
            raise PermissionDenied("Aucune activité spécifiée.")

        from apps.activities.models import Activity

        try:
            activity = Activity.objects.get(slug=activity_slug)
        except Activity.DoesNotExist:
            raise PermissionDenied("Activité introuvable.")

        if not user_has_activity_access(request.user, activity):
            raise PermissionDenied("Accès non autorisé à cette activité.")

        return super().dispatch(request, *args, **kwargs)


class UserCanAccessActivityMixin:
    """Mixin de base pour les vues filtrant sur une activité donnée.

    Accepte un slug d'activité dans l'URL ou dans le paramètre HTTP ``activity``.
    """

    activity_slug_kwarg = "activity_slug"

    def get_activity_from_request(self):
        activity_slug = self.kwargs.get(self.activity_slug_kwarg)
        if not activity_slug:
            activity_slug = self.request.GET.get("activity")
        if not activity_slug:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("Aucune activité spécifiée.")

        from apps.activities.models import Activity

        activity = Activity.objects.filter(slug=activity_slug).first()
        if activity is None:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("Activité introuvable.")

        if not user_has_activity_access(self.request.user, activity):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("Accès non autorisé à cette activité.")

        return activity