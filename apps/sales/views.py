"""Vues des ventes (JED-07).

Toutes les vues sont protégées par ``ActivityAccessRequiredMixin`` : un
utilisateur ne peut créer ou consulter des tickets que pour ses activités
autorisées (JED-03).
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, View

from apps.activities.models import Activity
from apps.accounts.permissions import (
    ActivityAccessRequiredMixin,
    user_is_employee_in_activity,
)
from apps.catalog.models import Product, Service

from .forms import SaleCancellationForm, SaleLineFormSet
from .models import Sale, SaleCancellation, SaleLine
from .services import cancel_sale, create_sale


class SaleListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = Sale
    template_name = "sales/sale_list.html"
    context_object_name = "sales"
    activity_slug_kwarg = "activity_slug"
    paginate_by = 25

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        cancellations = SaleCancellation.objects.filter(sale_id=OuterRef("pk"))
        queryset = Sale.objects.filter(activity=self.activity).annotate(
            _is_canceled=Exists(cancellations)
        )
        if user_is_employee_in_activity(self.request.user, self.activity):
            queryset = queryset.filter(user=self.request.user)
        return queryset.select_related("user").order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        return context


class SaleDetailView(LoginRequiredMixin, ActivityAccessRequiredMixin, DetailView):
    model = Sale
    template_name = "sales/sale_detail.html"
    context_object_name = "sale"
    activity_slug_kwarg = "activity_slug"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        queryset = Sale.objects.filter(activity=self.activity)
        if user_is_employee_in_activity(self.request.user, self.activity):
            queryset = queryset.filter(user=self.request.user)
        return queryset.select_related("user").prefetch_related("lines")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        return context


class SaleCancellationCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, View):
    activity_slug_kwarg = "activity_slug"
    template_name = "sales/sale_cancel_form.html"

    def get_sale(self, request):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        self.sale = get_object_or_404(
            Sale.objects.filter(activity=self.activity).select_related("user"),
            pk=self.kwargs["pk"],
        )
        if (
            user_is_employee_in_activity(request.user, self.activity)
            and self.sale.user_id != request.user.pk
        ):
            raise PermissionDenied("Un employé ne peut annuler que ses propres ventes.")
        return self.sale

    def get(self, request, *args, **kwargs):
        self.get_sale(request)
        if self.sale.is_canceled:
            return redirect("sales:sale_detail", activity_slug=self.activity.slug, pk=self.sale.pk)
        return self.render(request, SaleCancellationForm())

    def post(self, request, *args, **kwargs):
        self.get_sale(request)
        form = SaleCancellationForm(request.POST)
        if form.is_valid():
            try:
                cancellation = cancel_sale(self.sale, request.user, form.cleaned_data["reason"])
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, f"Ticket #{self.sale.pk} annulé.")
                return redirect(
                    "sales:sale_cancellation_detail",
                    activity_slug=self.activity.slug,
                    pk=cancellation.pk,
                )
        return self.render(request, form)

    def render(self, request, form):
        from django.template.response import TemplateResponse

        return TemplateResponse(
            request,
            self.template_name,
            {"activity": self.activity, "sale": self.sale, "form": form},
        )


class SaleCancellationListView(LoginRequiredMixin, ActivityAccessRequiredMixin, ListView):
    model = SaleCancellation
    template_name = "sales/sale_cancellation_list.html"
    context_object_name = "cancellations"
    activity_slug_kwarg = "activity_slug"
    paginate_by = 25

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        queryset = SaleCancellation.objects.filter(sale__activity=self.activity)
        if user_is_employee_in_activity(self.request.user, self.activity):
            queryset = queryset.filter(user=self.request.user, sale__user=self.request.user)
        return queryset.select_related("sale", "sale__user", "user").order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        return context


class SaleCancellationDetailView(LoginRequiredMixin, ActivityAccessRequiredMixin, DetailView):
    model = SaleCancellation
    template_name = "sales/sale_cancellation_detail.html"
    context_object_name = "cancellation"
    activity_slug_kwarg = "activity_slug"

    def get_queryset(self):
        self.activity = get_object_or_404(Activity, slug=self.kwargs["activity_slug"])
        queryset = SaleCancellation.objects.filter(sale__activity=self.activity)
        if user_is_employee_in_activity(self.request.user, self.activity):
            queryset = queryset.filter(user=self.request.user, sale__user=self.request.user)
        return queryset.select_related("sale", "sale__user", "user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity"] = self.activity
        return context


class SaleCreateView(LoginRequiredMixin, ActivityAccessRequiredMixin, View):
    """Création d'un ticket de caisse : produits et/ou services (A7).

    Le formulaire utilise un *formset* de lignes. La création est délivrée par
    le service central ``create_sale`` (transaction atomique) : un échec sur
    une ligne annule l'ensemble du ticket.
    """

    template_name = "sales/sale_form.html"
    activity_slug_kwarg = "activity_slug"

    def get(self, request, *args, **kwargs):
        self.activity = get_object_or_404(Activity, slug=kwargs["activity_slug"])
        formset = SaleLineFormSet(form_kwargs={"activity": self.activity}, prefix="form")
        return self.render(request, formset)

    def post(self, request, *args, **kwargs):
        self.activity = get_object_or_404(Activity, slug=kwargs["activity_slug"])
        formset = SaleLineFormSet(
            request.POST, form_kwargs={"activity": self.activity}, prefix="form"
        )
        if formset.is_valid():
            lines_data = []
            for cleaned in formset.cleaned_data:
                if not cleaned:
                    continue
                product = cleaned.get("product")
                service = cleaned.get("service")
                quantity = cleaned.get("quantity")
                if not product and not service:
                    continue
                if quantity is None or quantity <= 0:
                    continue
                lines_data.append({"item": product or service, "quantity": quantity})

            if not lines_data:
                formset.add_error(None, "Le ticket doit contenir au moins un produit ou un service.")
                return self.render(request, formset)

            try:
                sale = create_sale(
                    activity=self.activity,
                    user=request.user,
                    lines_data=lines_data,
                )
            except (ValidationError, IntegrityError, ValueError) as exc:
                formset.add_error(None, str(exc))
                return self.render(request, formset)

            messages.success(
                request,
                f"Ticket #{sale.pk} enregistré — total {sale.total} €.",
            )
            return redirect(
                "sales:sale_detail",
                activity_slug=self.activity.slug,
                pk=sale.pk,
            )
        return self.render(request, formset)

    def render(self, request, formset):
        from django.template.response import TemplateResponse

        return TemplateResponse(
            request,
            self.template_name,
            {
                "activity": self.activity,
                "formset": formset,
                "products": Product.objects.filter(activity=self.activity, is_active=True),
                "services": Service.objects.filter(activity=self.activity, is_active=True),
            },
        )
