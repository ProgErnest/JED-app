from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import DecimalField, Exists, F, OuterRef, Sum
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.activities.models import Activity
from apps.accounts.permissions import user_is_global
from apps.inventory.models import StockMovement
from apps.sales.models import Sale, SaleCancellation

from .services import (
    accessible_dashboard_activities,
    activity_dashboard_metrics,
    activity_operational_details,
    global_employee_metrics,
    global_activity_metrics,
    global_item_metrics,
)


def get_date_range(request):
    today = timezone.localdate()
    default_start = today - timedelta(days=29)
    start_value = request.GET.get("start")
    end_value = request.GET.get("end")
    try:
        start_date = date.fromisoformat(start_value) if start_value else default_start
        end_date = date.fromisoformat(end_value) if end_value else today
    except ValueError as exc:
        raise PermissionDenied("Format de date invalide. Utilisez AAAA-MM-JJ.") from exc

    if start_date > end_date:
        raise PermissionDenied("La date de début doit précéder la date de fin.")
    if (end_date - start_date).days > 366:
        raise PermissionDenied("La période ne peut pas dépasser 367 jours.")
    return start_date, end_date


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/dashboard_home.html"

    def get(self, request, *args, **kwargs):
        activities = accessible_dashboard_activities(request.user)
        if user_is_global(request.user):
            return redirect("analytics:global-dashboard")
        first_activity = activities.first()
        if first_activity is None:
            raise PermissionDenied("Aucune activité accessible.")
        return redirect("analytics:activity-dashboard", activity_slug=first_activity.slug)


class ActivityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/activity_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date, end_date = get_date_range(self.request)
        activity, metrics = activity_dashboard_metrics(
            self.request.user,
            self.kwargs["activity_slug"],
            start_date,
            end_date,
        )
        operational_details = activity_operational_details(
            self.request.user,
            activity,
            start_date,
            end_date,
        )
        context.update(
            {
                "activity": activity,
                "metrics": metrics,
                "activities": accessible_dashboard_activities(self.request.user),
                **operational_details,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return context


class GlobalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/global_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not user_is_global(request.user):
            raise PermissionDenied("Cette vue est réservée au gérant global.")
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def get_period_dates(period, today):
        if period == "week":
            start_date = today - timedelta(days=today.weekday())
        elif period == "month":
            start_date = today.replace(day=1)
        else:
            period = "day"
            start_date = today
        return period, start_date, today

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period, start_date, end_date = self.get_period_dates(
            self.request.GET.get("period", "day"),
            timezone.localdate(),
        )
        previous_end = start_date - timedelta(days=1)
        previous_start = previous_end - (end_date - start_date)
        rows = global_activity_metrics(self.request.user, start_date, end_date)
        previous_rows = global_activity_metrics(
            self.request.user,
            previous_start,
            previous_end,
        )
        previous_by_activity = {row["activity"].pk: row for row in previous_rows}
        for row in rows:
            previous = previous_by_activity.get(row["activity"].pk, {})
            previous_revenue = previous.get("revenue", Decimal("0.00"))
            previous_margin = previous.get("estimated_margin", Decimal("0.00"))
            row["previous_revenue"] = previous_revenue
            row["revenue_change"] = row["revenue"] - previous_revenue
            row["revenue_change_percent"] = (
                row["revenue_change"] / previous_revenue * 100
                if previous_revenue
                else None
            )
            row["margin_change"] = row["estimated_margin"] - previous_margin
        totals = {
            key: sum((row[key] for row in rows), start=Decimal("0.00"))
            for key in ("revenue", "sale_count", "estimated_margin", "stock_purchases")
        }
        previous_revenue_total = sum(
            (row["revenue"] for row in previous_rows),
            start=Decimal("0.00"),
        )
        totals["previous_revenue"] = previous_revenue_total
        totals["revenue_change"] = totals["revenue"] - previous_revenue_total
        totals["revenue_change_percent"] = (
            totals["revenue_change"] / previous_revenue_total * 100
            if previous_revenue_total
            else None
        )
        totals["stock_entry_count"] = sum(row["stock_purchase_count"] for row in rows)
        item_rankings = global_item_metrics(self.request.user, start_date, end_date)
        employees = global_employee_metrics(self.request.user, start_date, end_date)
        context.update(
            {
                "rows": rows,
                "employees": employees[:5],
                "item_rankings": item_rankings,
                "totals": totals,
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                "previous_start": previous_start,
                "previous_end": previous_end,
            }
        )
        active_activities = Activity.objects.filter(is_active=True)
        canceled_sales = SaleCancellation.objects.filter(sale_id=OuterRef("pk"))
        recent_sales = Sale.objects.filter(
            activity__in=active_activities,
        ).annotate(_is_canceled=Exists(canceled_sales)).filter(
            _is_canceled=False
        ).select_related("activity", "user").prefetch_related(
            "lines__product", "lines__service"
        )
        recent_cancellations = SaleCancellation.objects.filter(
            sale__activity__in=active_activities,
        ).select_related("sale", "sale__activity", "user")
        recent_movements = StockMovement.objects.filter(
            activity__in=active_activities,
        ).exclude(movement_type=StockMovement.MovementType.EXIT).select_related(
            "activity", "user", "product"
        )
        recent_operations = []
        for sale in recent_sales.order_by("-created_at")[:12]:
            items = ", ".join(
                f"{line.item_display} × {line.quantity}" for line in sale.lines.all()
            )
            recent_operations.append(
                {
                    "kind": "sale",
                    "created_at": sale.created_at,
                    "activity": sale.activity,
                    "user": sale.user,
                    "label": f"Vente #{sale.pk}",
                    "detail": items or "Vente enregistrée",
                    "amount": sale.total,
                    "url": reverse(
                        "sales:sale_detail",
                        kwargs={"activity_slug": sale.activity.slug, "pk": sale.pk},
                    ),
                }
            )
        for cancellation in recent_cancellations.order_by("-created_at")[:12]:
            recent_operations.append(
                {
                    "kind": "cancellation",
                    "created_at": cancellation.created_at,
                    "activity": cancellation.sale.activity,
                    "user": cancellation.user,
                    "label": f"Annulation de la vente #{cancellation.sale_id}",
                    "detail": cancellation.reason,
                    "amount": None,
                    "url": reverse(
                        "sales:sale_detail",
                        kwargs={
                            "activity_slug": cancellation.sale.activity.slug,
                            "pk": cancellation.sale_id,
                        },
                    ),
                }
            )
        for movement in recent_movements.order_by("-created_at")[:12]:
            recent_operations.append(
                {
                    "kind": "stock",
                    "created_at": movement.created_at,
                    "activity": movement.activity,
                    "user": movement.user,
                    "label": movement.get_movement_type_display(),
                    "detail": f"{movement.product.name} · {movement.quantity:+d}",
                    "amount": None,
                    "url": None,
                }
            )
        context["recent_operations"] = sorted(
            recent_operations,
            key=lambda operation: operation["created_at"],
            reverse=True,
        )[:15]
        return context
