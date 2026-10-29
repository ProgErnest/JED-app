from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.expenses.models import Expense, ExpenseCategory
from apps.sales.models import Sale, SaleCancellation, SaleLine
from apps.analytics.services import dashboard_metrics, global_activity_metrics


class DashboardMetricsTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(
            name="Analytics Boutique JED-10",
            slug="analytics-boutique-jed10",
        )
        self.employee = User.objects.create_user("analytics-employee", password="test")
        ActivityMembership.objects.create(
            user=self.employee,
            activity=self.activity,
            role=Role.EMPLOYEE,
        )
        self.manager = User.objects.create_user("analytics-manager", password="test")
        ActivityMembership.objects.create(
            user=self.manager,
            activity=self.activity,
            role=Role.MANAGER,
        )
        self.category = ExpenseCategory.objects.create(
            activity=self.activity,
            name="Loyer analytics",
            slug="loyer-analytics-jed10",
        )
        self.today = date.today()

    def create_sale(self, user, total, *, canceled=False, lines=()):
        sale = Sale.objects.create(activity=self.activity, user=user, total=total)
        for unit_price, cost, quantity, reliable in lines:
            SaleLine.objects.create(
                sale=sale,
                quantity=quantity,
                unit_price=unit_price,
                cost=cost,
                margin_reliable=reliable,
                total=unit_price * quantity,
            )
        if canceled:
            SaleCancellation.objects.create(
                sale=sale,
                user=user,
                reason="Test cancellation",
            )
        return sale

    def test_metrics_exclude_canceled_sales_and_expenses_and_unreliable_margin(self):
        self.create_sale(
            self.employee,
            Decimal("30.00"),
            lines=[(Decimal("10.00"), Decimal("4.00"), 2, True)],
        )
        self.create_sale(
            self.manager,
            Decimal("50.00"),
            canceled=True,
            lines=[(Decimal("25.00"), Decimal("5.00"), 2, True)],
        )
        self.create_sale(
            self.employee,
            Decimal("20.00"),
            lines=[(Decimal("20.00"), Decimal("3.00"), 1, False)],
        )
        Expense.objects.create(
            activity=self.activity,
            category=self.category,
            user=self.employee,
            amount=Decimal("8.00"),
        )
        canceled_expense = Expense.objects.create(
            activity=self.activity,
            category=self.category,
            user=self.employee,
            amount=Decimal("90.00"),
        )
        canceled_expense.cancel(self.employee, "Saisie erronée")

        metrics = dashboard_metrics(
            self.manager,
            self.activity,
            self.today,
            self.today,
        )

        self.assertEqual(metrics["revenue"], Decimal("50.00"))
        self.assertEqual(metrics["sale_count"], 2)
        self.assertEqual(metrics["expenses"], Decimal("8.00"))
        self.assertEqual(metrics["expense_count"], 1)
        self.assertEqual(metrics["estimated_margin"], Decimal("12.00"))
        self.assertEqual(metrics["unreliable_line_count"], 1)
        self.assertEqual(metrics["reported_balance"], Decimal("42.00"))

    def test_employee_metrics_only_include_their_own_operations(self):
        self.create_sale(self.employee, Decimal("12.00"))
        self.create_sale(self.manager, Decimal("45.00"))
        Expense.objects.create(
            activity=self.activity,
            category=self.category,
            user=self.employee,
            amount=Decimal("2.00"),
        )
        Expense.objects.create(
            activity=self.activity,
            category=self.category,
            user=self.manager,
            amount=Decimal("7.00"),
        )

        metrics = dashboard_metrics(
            self.employee,
            self.activity,
            self.today,
            self.today,
        )

        self.assertEqual(metrics["revenue"], Decimal("12.00"))
        self.assertEqual(metrics["sale_count"], 1)
        self.assertEqual(metrics["expenses"], Decimal("2.00"))
        self.assertEqual(metrics["expense_count"], 1)
        self.assertTrue(metrics["employee_scope"])

    def test_global_metrics_are_split_by_activity(self):
        global_user = User.objects.create_user("analytics-global", password="test")
        ActivityMembership.objects.create(user=global_user, role=Role.GLOBAL)
        second_activity = Activity.objects.create(
            name="Analytics Coiffure JED-10",
            slug="analytics-coiffure-jed10",
        )
        self.create_sale(self.employee, Decimal("15.00"))

        rows = global_activity_metrics(
            global_user,
            self.today,
            self.today,
        )

        self.assertEqual(len(rows), Activity.objects.filter(is_active=True).count())
        metrics_by_slug = {row["activity"].slug: row for row in rows}
        self.assertEqual(metrics_by_slug[self.activity.slug]["revenue"], Decimal("15.00"))
        self.assertEqual(metrics_by_slug[second_activity.slug]["revenue"], Decimal("0.00"))
