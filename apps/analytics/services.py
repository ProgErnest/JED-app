from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum

from apps.accounts.permissions import (
    get_accessible_activities,
    user_has_activity_access,
    user_is_employee_in_activity,
    user_is_global,
)
from apps.activities.models import Activity
from apps.expenses.models import Expense
from apps.sales.models import Sale, SaleCancellation, SaleLine

ZERO = Decimal("0.00")


def dashboard_metrics(user, activity, start_date: date, end_date: date) -> dict:
    """Return scoped metrics for one activity and inclusive date range."""
    if not user_has_activity_access(user, activity):
        raise PermissionDenied("Accès non autorisé à cette activité.")
    sales = Sale.objects.filter(
        activity=activity,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).exclude(pk__in=SaleCancellation.objects.values("sale_id"))
    expenses = Expense.objects.filter(
        activity=activity,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        is_canceled=False,
    )

    employee_scope = user_is_employee_in_activity(user, activity)
    if employee_scope:
        sales = sales.filter(user=user)
        expenses = expenses.filter(user=user)

    sale_totals = sales.aggregate(
        revenue=Sum("total"),
        sale_count=Count("pk"),
    )
    expense_totals = expenses.aggregate(
        expense_total=Sum("amount"),
        expense_count=Count("pk"),
    )
    lines = SaleLine.objects.filter(sale__in=sales)
    reliable_lines = lines.filter(margin_reliable=True)
    line_margin = ExpressionWrapper(
        (F("unit_price") - F("cost")) * F("quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    margin_total = reliable_lines.aggregate(margin=Sum(line_margin))["margin"] or ZERO

    unreliable_line_count = lines.filter(margin_reliable=False).count()
    return {
        "revenue": sale_totals["revenue"] or ZERO,
        "sale_count": sale_totals["sale_count"],
        "expenses": expense_totals["expense_total"] or ZERO,
        "expense_count": expense_totals["expense_count"],
        "estimated_margin": margin_total,
        "unreliable_line_count": unreliable_line_count,
        "reliable_margin_line_count": reliable_lines.count(),
        "employee_scope": employee_scope,
        "reported_balance": (sale_totals["revenue"] or ZERO)
        - (expense_totals["expense_total"] or ZERO),
    }


def global_activity_metrics(user, start_date: date, end_date: date) -> list[dict]:
    if not user_is_global(user):
        raise PermissionDenied("Cette vue est réservée au gérant global.")
    activities = Activity.objects.filter(is_active=True).order_by("name")
    return [
        {
            "activity": activity,
            **dashboard_metrics(user, activity, start_date, end_date),
        }
        for activity in activities
    ]


def activity_dashboard_metrics(user, activity_slug: str, start_date: date, end_date: date) -> tuple[Activity, dict]:
    activity = Activity.objects.filter(slug=activity_slug, is_active=True).first()
    if activity is None or not user_has_activity_access(user, activity):
        raise PermissionDenied("Accès non autorisé à cette activité.")
    return activity, dashboard_metrics(user, activity, start_date, end_date)


def accessible_dashboard_activities(user):
    return get_accessible_activities(user).filter(is_active=True).order_by("name")
