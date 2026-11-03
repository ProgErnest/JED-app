"""Vues des mouvements de stock (JED-05).

Toutes les vues sont protégées par ``ActivityAccessRequiredMixin`` : un
utilisateur ne peut saisir des mouvements que pour ses activités autorisées.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Exists, F, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.activities.models import Activity
from apps.accounts.permissions import ActivityAccessRequiredMixin, user_is_employee_in_activity
from apps.catalog.models import Product
from .forms import StockCorrectionForm, StockEntryForm
from .models import StockMovement
from .services import record_stock_movement
from apps.sales.models import SaleLine


def products_with_daily_sales(activity):
    today = timezone.localdate()
    daily_sales = (
        SaleLine.objects.filter(
            product_id=OuterRef("pk"),
            sale__activity=activity,
            sale__created_at__date=today,
            sale__cancellation__isnull=True,
        )
        .values("product_id")
        .annotate(quantity_sold=Sum("quantity"))
        .values("quantity_sold")[:1]
    )
    purchase_entries = StockMovement.objects.filter(
        product_id=OuterRef("pk"),
        movement_type=StockMovement.MovementType.ENTRY,
        unit_cost__isnull=False,
    )
    return Product.objects.filter(activity=activity).annotate(
        daily_sold=Coalesce(
            Subquery(daily_sales, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        ),
        has_zero_purchase_cost=Exists(purchase_entries.filter(unit_cost=0)),
        has_positive_purchase_cost=Exists(purchase_entries.filter(unit_cost__gt=0)),
        unit_margin=F("price") - F("average_cost"),
    )


class StockMovementListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = Product
    template_name = "inventory/stock_overview.html"
    context_object_name = "products"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        queryset = products_with_daily_sales(self.activity)
        self.search_query = self.request.GET.get("q", "").strip()
        self.stock_filter = self.request.GET.get("stock", "all")
        self.sort = self.request.GET.get("sort", "name")
        if self.search_query:
            queryset = queryset.filter(
                Q(name__icontains=self.search_query) | Q(unit__icontains=self.search_query)
            )
        if self.stock_filter == "out":
            queryset = queryset.filter(stock_quantity__lte=0)
        elif self.stock_filter == "low":
            queryset = queryset.filter(stock_quantity__gt=0, stock_quantity__lte=F("daily_sold"))
        elif self.stock_filter == "available":
            queryset = queryset.filter(stock_quantity__gt=F("daily_sold"))
        sort_fields = {
            "name": ("name",),
            "stock_low": ("stock_quantity", "name"),
            "stock_high": ("-stock_quantity", "name"),
            "sold_high": ("-daily_sold", "name"),
        }
        if self.sort not in sort_fields:
            self.sort = "name"
        return queryset.order_by(*sort_fields[self.sort])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        context["search_query"] = self.search_query
        context["stock_filter"] = self.stock_filter
        context["sort"] = self.sort
        context["product_count"] = self.get_queryset().count()
        return context


class ProductStockDetailView(LoginRequiredMixin, ActivityAccessRequiredMixin, DetailView):
    model = Product
    template_name = "inventory/product_stock_detail.html"
    context_object_name = "product"
    activity_slug_kwarg = "activity_slug"
    slug_url_kwarg = "product_slug"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        return products_with_daily_sales(self.activity)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        movements = StockMovement.objects.filter(
            activity=self.activity,
            product=product,
        ).select_related("user")
        if user_is_employee_in_activity(self.request.user, self.activity):
            movements = movements.filter(user=self.request.user)

        self.movement_type = self.request.GET.get("type", "all")
        self.date_from = self.request.GET.get("from", "")
        self.date_to = self.request.GET.get("to", "")
        self.movement_search = self.request.GET.get("q", "").strip()
        self.date_error = ""
        valid_types = {choice[0] for choice in StockMovement.MovementType.choices}
        if self.movement_type in valid_types:
            movements = movements.filter(movement_type=self.movement_type)
        else:
            self.movement_type = "all"
        try:
            parsed_date_from = parse_date(self.date_from) if self.date_from else None
            parsed_date_to = parse_date(self.date_to) if self.date_to else None
        except ValueError:
            parsed_date_from = None
            parsed_date_to = None
        if self.date_from and not parsed_date_from or self.date_to and not parsed_date_to:
            self.date_error = "Vérifiez les dates du filtre."
        else:
            if parsed_date_from:
                movements = movements.filter(created_at__date__gte=parsed_date_from)
            if parsed_date_to:
                movements = movements.filter(created_at__date__lte=parsed_date_to)
        if self.movement_search:
            movements = movements.filter(
                Q(reason__icontains=self.movement_search)
                | Q(user__username__icontains=self.movement_search)
                | Q(user__first_name__icontains=self.movement_search)
                | Q(user__last_name__icontains=self.movement_search)
            )

        movement_count = movements.count()
        page = Paginator(movements.order_by("-created_at"), 50).get_page(
            self.request.GET.get("page")
        )
        page_query = self.request.GET.copy()
        page_query.pop("page", None)
        context.update(
            {
                "activity": self.activity,
                "movements": page.object_list,
                "page_obj": page,
                "paginator": page.paginator,
                "movement_type": self.movement_type,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "movement_search": self.movement_search,
                "date_error": self.date_error,
                "movement_types": StockMovement.MovementType.choices,
                "movement_count": movement_count,
                "page_query": page_query.urlencode(),
            }
        )
        return context


class StockEntryCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, CreateView):
    model = StockMovement
    form_class = StockEntryForm
    template_name = "inventory/movement_form.html"
    activity_slug_kwarg = "activity_slug"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        kwargs["activity"] = activity
        product_id = self.request.GET.get("product")
        if product_id and Product.objects.filter(pk=product_id, activity=activity).exists():
            kwargs.setdefault("initial", {})["product"] = product_id
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
        activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        kwargs["activity"] = activity
        product_id = self.request.GET.get("product")
        if product_id and Product.objects.filter(pk=product_id, activity=activity).exists():
            kwargs.setdefault("initial", {})["product"] = product_id
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        product_id = self.request.GET.get("product") or self.request.POST.get("product")
        current_product = None
        if product_id:
            current_product = Product.objects.filter(
                pk=product_id,
                activity=activity,
            ).first()
        context["activity"] = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        context["page_title"] = "Correction de stock"
        context["current_product"] = current_product
        return context

    def form_valid(self, form):
        form.instance.activity = get_object_or_404(
            Activity, slug=self.kwargs["activity_slug"]
        )
        form.instance.user = self.request.user
        try:
            corrected_product = record_stock_movement(
                product=form.instance.product,
                movement_type=form.instance.movement_type,
                unit_cost=None,
                user=self.request.user,
                reason=form.instance.reason,
                activity=form.instance.activity,
                counted_quantity=form.cleaned_data["counted_quantity"],
            )
        except Exception as exc:  # pragma: no cover - validation métier
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        if corrected_product._last_stock_movement is None:
            messages.info(
                self.request,
                "Aucune correction nécessaire : le stock compté correspond au stock enregistré.",
            )
        else:
            messages.success(
                self.request,
                f"Comptage enregistré. Écart appliqué : {corrected_product._last_stock_movement.quantity:+d}.",
            )
        return redirect(
            "inventory:product_stock_detail",
            activity_slug=self.kwargs["activity_slug"],
            product_slug=form.instance.product.slug,
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
