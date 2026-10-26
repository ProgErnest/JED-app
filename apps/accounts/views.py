"""
Vues de test manuel pour les permissions (JED-03).

Ces vues permettent de vérifier que les règles d'accès par rôle fonctionnent
côté serveur. Elles ne constituent pas l'interface finale (JED-11).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from .permissions import (
    activity_access_required,
    global_or_manager_required,
    ActivityAccessRequiredMixin,
    get_accessible_activities,
    user_is_global,
)
from apps.activities.models import Activity


@login_required
def home(request):
    """Page d'accueil : liste les activités accessibles à l'utilisateur connecté."""
    activities = get_accessible_activities(request.user)
    is_global = user_is_global(request.user)

    lines = [
        f"Utilisateur : {request.user.username}",
        f"Rôle global : {is_global}",
        "Activités accessibles :",
    ]
    for activity in activities:
        lines.append(f" - {activity.name} ({activity.slug})")
    if not activities:
        lines.append(" (aucune)")
    return HttpResponse("<br>".join(lines))


@login_required
@activity_access_required("activity_slug")
def activity_detail(request, activity_slug):
    """Détail d'une activité : accessible seulement si l'utilisateur y a droit."""
    activity = get_object_or_404(Activity, slug=activity_slug)
    return HttpResponse(
        f"Accès autorisé à l'activité : {activity.name}<br>"
        f"Description : {activity.description}"
    )


@login_required
@global_or_manager_required("activity_slug")
def activity_manage(request, activity_slug):
    """Gestion d'activité : réservé aux rôles GLOBAL et MANAGER sur cette activité."""
    activity = get_object_or_404(Activity, slug=activity_slug)
    return HttpResponse(
        f"Droits de gestion confirmés pour : {activity.name}<br>"
        f"Utilisateur : {request.user.username}"
    )


@method_decorator(login_required, name="dispatch")
class ActivityListView(View):
    """CBV listant les activités accessibles à l'utilisateur connecté."""

    def get(self, request):
        activities = get_accessible_activities(request.user)
        lines = [f"Activités accessibles pour {request.user.username} :"]
        for activity in activities:
            lines.append(f" - {activity.name}")
        return HttpResponse("<br>".join(lines))


@method_decorator(login_required, name="dispatch")
class ActivityAccessCBVView(ActivityAccessRequiredMixin, View):
    """CBV protégée par ActivityAccessRequiredMixin."""

    def get(self, request, activity_slug):
        activity = get_object_or_404(Activity, slug=activity_slug)
        return HttpResponse(f"CBV : accès autorisé à {activity.name}")
