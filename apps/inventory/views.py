"""Vues des mouvements de stock (JED-05).

Toutes les vues sont protégées par ``ActivityAccessRequiredMixin`` : un
utilisateur ne peut saisir des mouvements que pour ses activités autorisées.
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView

from apps.activities.models import Activity
from apps.accounts.permissions import (
    ActivityAccessRequiredMixin,
    user_is_employee_in_activity,
)
from .forms import StockCorrectionForm, StockEntryForm
from .models import StockMovement
from .services import record_stock_movement


class StockMovementListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = StockMovement
    template_name = "inventory/movement_list.html"
    context_object_name = "movements"
    activity_slug_kwarg = "activity_slug"
    paginate_by = 25

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        queryset = StockMovement.objects.filter(activity=self.activity)
        if user_is_employee_in_activity(self.request.user, self.activity):
            queryset = queryset.filter(user=self.request.user)
        return queryset.select_related("product", "user").order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        return context


class StockEntryCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    model = StockMovement
    form_class = StockEntryForm
    template_name = "inventory/movement_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        return context

    def form_valid(self, form):
        form.instance.activity = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        form.instance.user = self.request.user
        try:
            record_stock_movement(
                product=form.instance.product,
                movement_type=form.instance.movement_type,
                quantity=form.instance.quantity,
                unit_cost=form.instance.unit_cost,
                user=self.request.user,
                reason=form.instance.reason,
                activity=form.instance.activity,
            )
        except Exception as exc:  # pragma: no cover - validation métier
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect(
            "inventory:movement_list",
            activity_slug=self.kwargs["activity_slug"],
        )

    def get_success_url(self):
        return reverse(
            "inventory:movement_list",
            kwargs={"activity_slug": self.kwargs["activity_slug"]},
        )


class StockCorrectionCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    """Saisie d'une correction/perte de stock (JED-06).

    Le motif est obligatoire. La quantité est signée (ajout ou perte).
    """

    model = StockMovement
    form_class = StockCorrectionForm
    template_name = "inventory/movement_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        context["page_title"] = "Correction de stock"
        return context

    def form_valid(self, form):
        form.instance.activity = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        form.instance.user = self.request.user
        try:
            record_stock_movement(
                product=form.instance.product,
                movement_type=form.instance.movement_type,
                quantity=form.instance.quantity,
                unit_cost=None,
                user=self.request.user,
                reason=form.instance.reason,
                activity=form.instance.activity,
            )
        except Exception as exc:  # pragma: no cover - validation métier
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect(
            "inventory:movement_list",
            activity_slug=self.kwargs["activity_slug"],
        )

    def get_success_url(self):
        return reverse(
            "inventory:movement_list",
            kwargs={"activity_slug": self.kwargs["activity_slug"]},
        )


class InventoryHomeView(LoginRequiredMixin, View):
    """Page d'accueil de l'inventaire : redirige vers la première activité accessible."""

    def get(self, request):
        from apps.accounts.permissions import get_accessible_activities

        activities = get_accessible_activities(request.user)
        if activities.exists():
            return redirect(
                "inventory:movement_list",
                activity_slug=activities.first().slug,
            )
        from django.http import HttpResponse
        return HttpResponse("Aucune activité accessible.", status=403)
