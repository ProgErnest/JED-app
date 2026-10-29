from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.permissions import user_is_global

from .services import (
    accessible_dashboard_activities,
    activity_dashboard_metrics,
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
        context.update(
            {
                "activity": activity,
                "metrics": metrics,
                "activities": accessible_dashboard_activities(self.request.user),
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
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        context["totals"] = {
            key: sum((row[key] for row in context["rows"]), start=0)
            for key in ("revenue", "expenses", "estimated_margin", "reported_balance")
        }
        return context
