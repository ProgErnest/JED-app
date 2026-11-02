"""
Vues de test manuel pour les permissions (JED-03).

Ces vues permettent de vérifier que les règles d'accès par rôle fonctionnent
côté serveur. Elles ne constituent pas l'interface finale (JED-11).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from .permissions import (
    activity_access_required,
    global_or_manager_required,
    ActivityAccessRequiredMixin,
    get_accessible_activities,
    user_is_global,
    user_can_manage_team,
    get_user_memberships,
)
from .models import ActivityMembership, Role
from .team_forms import TeamMembershipForm
from apps.activities.models import Activity


def entrypoint(request):
    """Dirige la racine vers la connexion ou l'espace adapté au rôle."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if user_is_global(request.user) or get_user_memberships(request.user).filter(
        role=Role.MANAGER
    ).exists():
        return redirect("analytics:home")
    return redirect("accounts:home")


@login_required
def home(request):
    """Page d'accueil : liste les activités accessibles à l'utilisateur connecté."""
    activities = get_accessible_activities(request.user)
    is_global = user_is_global(request.user)
    memberships = get_user_memberships(request.user)
    if (
        not is_global
        and memberships.count() == 1
        and memberships.filter(role=Role.EMPLOYEE).exists()
    ):
        activity = memberships.select_related("activity").first().activity
        if activity.is_active:
            return redirect("sales:sale_add", activity_slug=activity.slug)

    return render(
        request,
        "accounts/home.html",
        {
            "activities": activities,
            "is_global": is_global,
            "managed_activity_ids": list(
                get_user_memberships(request.user)
                .filter(role=Role.MANAGER, activity__is_active=True)
                .values_list("activity_id", flat=True)
            ),
        },
    )


@login_required
def team_list(request, activity_slug=None):
    is_global = user_is_global(request.user)
    if is_global:
        memberships = ActivityMembership.objects.filter(
            is_active=True,
            user__is_active=True,
        ).select_related("user", "activity")
        if activity_slug:
            memberships = memberships.filter(activity__slug=activity_slug)
        activities = Activity.objects.filter(is_active=True)
        selected_activity = (
            get_object_or_404(Activity, slug=activity_slug) if activity_slug else None
        )
    else:
        selected_activity = None
        activities = Activity.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
            memberships__role=Role.MANAGER,
            is_active=True,
        ).distinct()
        if activity_slug:
            selected_activity = activities.filter(slug=activity_slug).first()
            if selected_activity is None:
                raise PermissionDenied("Vous ne gérez pas cette activité.")
        elif activities.count() == 1:
            selected_activity = activities.first()
        elif activities.count() > 1:
            return render(
                request,
                "accounts/team_activity_select.html",
                {"activities": activities},
            )
        else:
            raise PermissionDenied("La gestion des comptes est réservée au responsable.")
        memberships = ActivityMembership.objects.filter(
            activity__in=activities,
            is_active=True,
            user__is_active=True,
        ).select_related("user", "activity")

    if selected_activity:
        memberships = memberships.filter(activity=selected_activity)
    return render(
        request,
        "accounts/team_list.html",
        {
            "memberships": memberships,
            "activities": activities,
            "selected_activity": selected_activity,
            "is_global": is_global,
        },
    )


@login_required
def team_create(request, activity_slug=None):
    is_global = user_is_global(request.user)
    activity = _team_activity_for_user(request.user, activity_slug, is_global)
    form = TeamMembershipForm(
        request.POST or None,
        activity=activity,
        global_admin=is_global,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            membership = form.save()
        messages.success(request, f"Accès créé pour {membership.user.username}.")
        return redirect(_team_list_url(is_global, membership.activity))
    return render(
        request,
        "accounts/team_form.html",
        {"form": form, "is_global": is_global, "activity": activity},
    )


@login_required
def team_edit(request, membership_id):
    membership = _membership_for_manager(request.user, membership_id)
    if membership.user_id == request.user.pk:
        raise PermissionDenied("Vous ne pouvez pas modifier votre propre rôle ou accès.")
    is_global = user_is_global(request.user)
    activity = membership.activity
    form = TeamMembershipForm(
        request.POST or None,
        activity=activity,
        membership=membership,
        global_admin=is_global,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            membership = form.save()
        messages.success(request, f"Accès mis à jour pour {membership.user.username}.")
        return redirect(_team_list_url(is_global, membership.activity))
    return render(
        request,
        "accounts/team_form.html",
        {"form": form, "is_global": is_global, "activity": activity, "membership": membership},
    )


@login_required
def team_deactivate(request, membership_id):
    if request.method != "POST":
        raise PermissionDenied("Cette action doit être envoyée par formulaire.")
    membership = _membership_for_manager(request.user, membership_id)
    if membership.user_id == request.user.pk:
        raise PermissionDenied("Vous ne pouvez pas désactiver votre propre accès.")
    is_global = user_is_global(request.user)
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    messages.success(request, f"Accès désactivé pour {membership.user.username}.")
    return redirect(_team_list_url(is_global, membership.activity))


@login_required
def account_deactivate(request, user_id):
    if request.method != "POST" or not user_is_global(request.user):
        raise PermissionDenied("Seul le gérant global peut désactiver un compte.")
    user = get_object_or_404(User, pk=user_id)
    if user.pk == request.user.pk:
        raise PermissionDenied("Vous ne pouvez pas désactiver votre propre compte.")
    user.is_active = False
    user.save(update_fields=["is_active"])
    messages.success(request, f"Compte désactivé pour {user.username}.")
    return redirect("accounts:team_global")


def _team_activity_for_user(user, activity_slug, is_global):
    if is_global:
        if activity_slug:
            return get_object_or_404(Activity, slug=activity_slug, is_active=True)
        return None
    if not activity_slug:
        managed = Activity.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
            memberships__role=Role.MANAGER,
            is_active=True,
        )
        if managed.count() == 1:
            return managed.first()
        raise PermissionDenied("Une activité gérée doit être précisée.")
    activity = get_object_or_404(Activity, slug=activity_slug, is_active=True)
    if not user_can_manage_team(user, activity):
        raise PermissionDenied("Vous ne gérez pas cette activité.")
    return activity


def _membership_for_manager(user, membership_id):
    membership = get_object_or_404(
        ActivityMembership.objects.select_related("user", "activity"),
        pk=membership_id,
    )
    if user_is_global(user):
        return membership
    if membership.activity_id is None or not user_can_manage_team(user, membership.activity):
        raise PermissionDenied("Vous ne pouvez pas gérer cet accès.")
    return membership


def _team_list_url(is_global, activity):
    if is_global:
        return reverse("accounts:team_global")
    return reverse("accounts:team_activity", kwargs={"activity_slug": activity.slug})


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
