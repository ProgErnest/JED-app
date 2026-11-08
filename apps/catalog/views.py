"""Vues du catalogue — projet JED (JED-04).

Toutes les vues sont protégées par ``ActivityAccessRequiredMixin`` :
un utilisateur ne peut créer/consulter que les produits/services de ses
activités autorisées (voir JED-03).
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Exists, OuterRef
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.activities.models import Activity
from apps.accounts.permissions import (
    ActivityAccessRequiredMixin,
    user_can_manage_team,
)
from apps.inventory.models import StockMovement
from .forms import CatalogCategoryForm, ProductForm, ServiceForm
from .models import CatalogCategory, Product, Service


class CatalogCategoryListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = CatalogCategory
    template_name = "catalog/category_list.html"
    context_object_name = "categories"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return CatalogCategory.objects.filter(activity=self.activity).annotate(
            product_count=Count("products", distinct=True),
            service_count=Count("services", distinct=True),
        ).order_by("sort_order", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        context["can_manage_categories"] = user_can_manage_team(
            self.request.user, self.activity
        )
        return context


class CatalogManagerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        activity = get_object_or_404(Activity, slug=kwargs["activity_slug"])
        if not user_can_manage_team(request.user, activity):
            raise PermissionDenied("Seul un responsable peut gérer les rubriques.")
        return super().dispatch(request, *args, **kwargs)


class CatalogCategoryCreateView(LoginRequiredMixin, CatalogManagerRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    model = CatalogCategory
    form_class = CatalogCategoryForm
    template_name = "catalog/category_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_activity(self):
        return get_object_or_404(Activity, slug=self.kwargs["activity_slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.get_activity()
        return context

    def form_valid(self, form):
        form.instance.activity = self.get_activity()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("catalog:category_list", kwargs={"activity_slug": self.kwargs["activity_slug"]})


class CatalogCategoryUpdateView(LoginRequiredMixin, CatalogManagerRequiredMixin, ActivityAccessRequiredMixin, UpdateView):
    model = CatalogCategory
    form_class = CatalogCategoryForm
    template_name = "catalog/category_form.html"
    activity_slug_kwarg = "activity_slug"
    slug_url_kwarg = "category_slug"

    def get_queryset(self):
        return CatalogCategory.objects.filter(activity__slug=self.kwargs["activity_slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return context

    def get_success_url(self):
        return reverse("catalog:category_list", kwargs={"activity_slug": self.kwargs["activity_slug"]})


class ProductListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        self.categories = CatalogCategory.objects.filter(activity=self.activity)
        purchase_entries = StockMovement.objects.filter(
            product_id=OuterRef("pk"),
            movement_type=StockMovement.MovementType.ENTRY,
            unit_cost__isnull=False,
        )
        queryset = (
            Product.objects.filter(activity=self.activity)
            .annotate(
                has_zero_purchase_cost=Exists(purchase_entries.filter(unit_cost=0)),
                has_positive_purchase_cost=Exists(purchase_entries.filter(unit_cost__gt=0)),
            )
            .select_related("category")
            .order_by("name")
        )
        self.category_filter = self.request.GET.get("category", "all")
        if self.category_filter == "none":
            return queryset.filter(category__isnull=True)
        if self.category_filter.isdigit():
            return queryset.filter(
                category_id=self.category_filter,
                category__activity=self.activity,
            )
        self.category_filter = "all"
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        context["categories"] = self.categories
        context["category_filter"] = self.category_filter
        return context


class ProductCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return kwargs

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return kwargs

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
        self.categories = CatalogCategory.objects.filter(activity=self.activity)
        queryset = (
            Service.objects.filter(activity=self.activity)
            .select_related("category")
            .order_by("name")
        )
        self.category_filter = self.request.GET.get("category", "all")
        if self.category_filter == "none":
            return queryset.filter(category__isnull=True)
        if self.category_filter.isdigit():
            return queryset.filter(
                category_id=self.category_filter,
                category__activity=self.activity,
            )
        self.category_filter = "all"
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        context["categories"] = self.categories
        context["category_filter"] = self.category_filter
        return context


class ServiceCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = "catalog/service_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return kwargs

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["activity"] = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return kwargs

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
