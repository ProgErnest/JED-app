"""Vues du catalogue — projet JED (JED-04).

Toutes les vues sont protégées par ``ActivityAccessRequiredMixin`` :
un utilisateur ne peut créer/consulter que les produits/services de ses
activités autorisées (voir JED-03).
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.activities.models import Activity
from apps.accounts.permissions import ActivityAccessRequiredMixin
from .forms import ProductForm, ServiceForm
from .models import Product, Service


class ProductListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return Product.objects.filter(activity=self.activity).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        return context


class ProductCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_activity(self):
        return get_object_or_404(Activity, slug=self.kwargs["activity_slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity()
        return context

    def form_valid(self, form):
        form.instance.activity = self.get_activity()
        form.instance._current_user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "catalog:product_list",
            kwargs={"activity_slug": self.kwargs["activity_slug"]},
        )


class ProductUpdateView(LoginRequiredMixin, ActivityAccessRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        return Product.objects.filter(
            activity__slug=self.kwargs["activity_slug"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        return context

    def form_valid(self, form):
        form.instance._current_user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "catalog:product_list",
            kwargs={"activity_slug": self.kwargs["activity_slug"]},
        )


class ServiceListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = Service
    template_name = "catalog/service_list.html"
    context_object_name = "services"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return Service.objects.filter(activity=self.activity).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        return context


class ServiceCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = "catalog/service_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_activity(self):
        return get_object_or_404(Activity, slug=self.kwargs["activity_slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity()
        return context

    def form_valid(self, form):
        form.instance.activity = self.get_activity()
        form.instance._current_user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "catalog:service_list",
            kwargs={"activity_slug": self.kwargs["activity_slug"]},
        )


class ServiceUpdateView(LoginRequiredMixin, ActivityAccessRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = "catalog/service_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        return Service.objects.filter(
            activity__slug=self.kwargs["activity_slug"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        return context

    def form_valid(self, form):
        form.instance._current_user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "catalog:service_list",
            kwargs={"activity_slug": self.kwargs["activity_slug"]},
        )


class CatalogHomeView(LoginRequiredMixin, View):
    """Page d'accueil du catalogue : redirige vers la première activité accessible."""

    def get(self, request: HttpRequest) -> HttpResponse:
        from apps.accounts.permissions import get_accessible_activities

        activities = get_accessible_activities(request.user)
        if activities.exists():
            return redirect(
                "catalog:product_list",
                activity_slug=activities.first().slug,
            )
        return HttpResponse("Aucune activité accessible.", status=403)
