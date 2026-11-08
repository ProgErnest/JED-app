from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.permissions import user_is_global

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
        previous_end = start_date - timedelta(days=1)
        previous_start = previous_end - (end_date - start_date)
        _, previous_metrics = activity_dashboard_metrics(
            self.request.user,
            self.kwargs["activity_slug"],
            previous_start,
            previous_end,
        )
        metrics["previous_revenue"] = previous_metrics["revenue"]
        metrics["revenue_change"] = metrics["revenue"] - metrics["previous_revenue"]
        metrics["revenue_change_abs"] = abs(metrics["revenue_change"])
        metrics["revenue_change_percent"] = (
            metrics["revenue_change"] / metrics["previous_revenue"] * 100
            if metrics["previous_revenue"]
            else None
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
                "previous_start": previous_start,
                "previous_end": previous_end,
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

    @staticmethod
    def get_previous_period_dates(period, start_date, end_date):
        if period == "week":
            previous_start = start_date - timedelta(days=7)
            previous_end = previous_start + (end_date - start_date)
            return previous_start, previous_end
        if period == "month":
            previous_month_end = start_date - timedelta(days=1)
            previous_start = previous_month_end.replace(day=1)
            elapsed_days = (end_date - start_date).days
            previous_end = min(
                previous_start + timedelta(days=elapsed_days),
                previous_month_end,
            )
            return previous_start, previous_end
        previous_day = start_date - timedelta(days=1)
        return previous_day, previous_day

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period, start_date, end_date = self.get_period_dates(
            self.request.GET.get("period", "day"),
            timezone.localdate(),
        )
        previous_start, previous_end = self.get_previous_period_dates(
            period,
            start_date,
            end_date,
        )
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
            row["revenue_change_abs"] = abs(row["revenue_change"])
            row["revenue_change_percent"] = (
                row["revenue_change"] / previous_revenue * 100
                if previous_revenue
                else None
            )
            row["margin_change"] = row["estimated_margin"] - previous_margin
        totals = {
            "revenue": sum((row["revenue"] for row in rows), start=Decimal("0.00")),
            "sale_count": sum(row["sale_count"] for row in rows),
            "estimated_margin": sum(
                (row["estimated_margin"] for row in rows),
                start=Decimal("0.00"),
            ),
            "stock_purchases": sum(
                (row["stock_purchases"] for row in rows),
                start=Decimal("0.00"),
            ),
            "product_line_count": sum(row["product_line_count"] for row in rows),
            "reliable_margin_line_count": sum(
                row["reliable_margin_line_count"] for row in rows
            ),
        }
        totals["margin_coverage_percent"] = (
            totals["reliable_margin_line_count"] / totals["product_line_count"] * 100
            if totals["product_line_count"]
            else None
        )
        previous_revenue_total = sum(
            (row["revenue"] for row in previous_rows),
            start=Decimal("0.00"),
        )
        totals["previous_revenue"] = previous_revenue_total
        totals["revenue_change"] = totals["revenue"] - previous_revenue_total
        totals["revenue_change_abs"] = abs(totals["revenue_change"])
        totals["revenue_change_percent"] = (
            totals["revenue_change"] / previous_revenue_total * 100
            if previous_revenue_total
            else None
        )
        totals["stock_entry_count"] = sum(row["stock_purchase_count"] for row in rows)
        item_rankings = global_item_metrics(self.request.user, start_date, end_date)
        employees = global_employee_metrics(self.request.user, start_date, end_date)
        employees = sorted(
            (employee for employee in employees if employee["sale_count"]),
            key=lambda employee: (
                employee["revenue"],
                employee["sale_count"],
                employee["last_operation"],
            ),
            reverse=True,
        )
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
        return context
