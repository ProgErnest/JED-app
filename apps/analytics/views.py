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
from apps.expenses.models import Expense, ExpenseAuditLog
from apps.inventory.models import StockMovement
from apps.sales.models import Sale, SaleCancellation

from .services import (
    accessible_dashboard_activities,
    activity_dashboard_metrics,
    activity_operational_details,
    global_employee_metrics,
    global_activity_metrics,
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date, end_date = get_date_range(self.request)
        context.update(
            {
                "rows": global_activity_metrics(self.request.user, start_date, end_date),
                "employees": global_employee_metrics(self.request.user, start_date, end_date),
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        context["totals"] = {
            key: sum((row[key] for row in context["rows"]), start=0)
            for key in (
                "revenue",
                "expenses",
                "estimated_margin",
                "reported_balance",
                "stock_purchases",
            )
        }
        today = timezone.localdate()
        active_activities = Activity.objects.filter(is_active=True)
        canceled_sales = SaleCancellation.objects.filter(sale_id=OuterRef("pk"))
        today_sales = Sale.objects.filter(
            activity__in=active_activities,
            created_at__date=today,
        ).annotate(_is_canceled=Exists(canceled_sales))
        today_sales = today_sales.filter(_is_canceled=False)
        today_expenses = Expense.objects.filter(
            activity__in=active_activities,
            created_at__date=today,
            is_canceled=False,
        )
        today_stock_entries = StockMovement.objects.filter(
            activity__in=active_activities,
            movement_type=StockMovement.MovementType.ENTRY,
            unit_cost__isnull=False,
            created_at__date=today,
        )
        context["today_totals"] = {
            "revenue": today_sales.aggregate(total=Sum("total"))["total"] or Decimal("0.00"),
            "sale_count": today_sales.count(),
            "expenses": today_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "expense_count": today_expenses.count(),
            "stock_purchases": today_stock_entries.aggregate(
                total=Sum(
                    F("quantity") * F("unit_cost"),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                )
            )["total"] or Decimal("0.00"),
            "stock_entry_count": today_stock_entries.count(),
        }
        context["today_totals"]["reported_balance"] = (
            context["today_totals"]["revenue"] - context["today_totals"]["expenses"]
        )
        context["today_date"] = today

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
        recent_expense_events = ExpenseAuditLog.objects.filter(
            expense__activity__in=active_activities,
        ).select_related("expense", "expense__activity", "expense__category", "user")
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
        for event in recent_expense_events.order_by("-created_at")[:18]:
            expense = event.expense
            recent_operations.append(
                {
                    "kind": "expense",
                    "created_at": event.created_at,
                    "activity": expense.activity,
                    "user": event.user,
                    "label": f"Dépense · {expense.category.name} · {event.get_action_display()}",
                    "detail": event.reason or expense.description or "Dépense enregistrée",
                    "amount": -expense.amount if event.action == ExpenseAuditLog.Action.CREATED else None,
                    "url": reverse(
                        "expenses:expense-detail",
                        kwargs={"pk": expense.pk},
                    ) + f"?activity={expense.activity.slug}",
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
