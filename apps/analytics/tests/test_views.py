from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.analytics.services import dashboard_metrics
from apps.expenses.models import ExpenseCategory
from apps.sales.models import Sale


class DashboardViewTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(
            name="Analytics View Boutique JED-10",
            slug="analytics-view-boutique-jed10",
        )
        self.employee = User.objects.create_user("view-employee", password="test")
        ActivityMembership.objects.create(
            user=self.employee,
            activity=self.activity,
            role=Role.EMPLOYEE,
        )
        self.manager = User.objects.create_user("view-manager", password="test")
        ActivityMembership.objects.create(
            user=self.manager,
            activity=self.activity,
            role=Role.MANAGER,
        )

    def test_activity_dashboard_requires_login(self):
        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )
        self.assertEqual(response.status_code, 302)

    def test_user_without_activity_access_is_denied(self):
        unrelated = User.objects.create_user("unrelated", password="test")
        self.client.force_login(unrelated)
        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )
        self.assertEqual(response.status_code, 403)

    def test_employee_can_view_own_activity_dashboard(self):
        self.client.force_login(self.employee)
        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vos opérations uniquement")
        self.assertContains(response, "Marge brute estimée")

    def test_global_dashboard_is_for_global_role_only(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("analytics:global-dashboard"))
        self.assertEqual(response.status_code, 403)

        global_user = User.objects.create_user("view-global", password="test")
        ActivityMembership.objects.create(user=global_user, role=Role.GLOBAL)
        self.client.force_login(global_user)
        response = self.client.get(reverse("analytics:global-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.activity.name)

    def test_invalid_date_range_is_rejected(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug]),
            {"start": "2026-02-02", "end": "2026-02-01"},
        )
        self.assertEqual(response.status_code, 403)

    def test_dashboard_defaults_to_recent_thirty_days(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("start_date", response.context)
        self.assertEqual((response.context["end_date"] - response.context["start_date"]).days, 29)
