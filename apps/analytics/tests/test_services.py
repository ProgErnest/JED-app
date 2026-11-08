from datetime import datetime, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.catalog.models import Product
from apps.catalog.models import Service
from apps.expenses.models import Expense, ExpenseCategory
from apps.sales.models import Sale, SaleCancellation, SaleLine
from apps.analytics.services import (
    activity_operational_details,
    dashboard_metrics,
    global_activity_metrics,
    global_item_metrics,
)


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
        self.test_product = Product.objects.create(
            activity=self.activity,
            name="Produit test analytics",
            slug="produit-test-analytics",
            unit="pièce",
            price=Decimal("20.00"),
        )
        self.today = timezone.localdate()

    def create_sale(self, user, total, *, canceled=False, lines=()):
        sale = Sale.objects.create(activity=self.activity, user=user, total=total)
        for unit_price, cost, quantity, reliable in lines:
            SaleLine.objects.create(
                sale=sale,
                product=self.test_product,
                quantity=quantity,
                unit_price=unit_price,
                cost=cost,
                margin_reliable=reliable,
                total=unit_price * quantity,
            )
        Sale.objects.filter(pk=sale.pk).update(
            created_at=timezone.make_aware(datetime.combine(self.today, time(12, 0)))
        )
        sale.refresh_from_db()
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
        self.assertEqual(metrics["expenses"], Decimal("0.00"))
        self.assertEqual(metrics["expense_count"], 0)
        self.assertEqual(metrics["estimated_margin"], Decimal("12.00"))
        self.assertEqual(metrics["unreliable_line_count"], 1)
        self.assertEqual(metrics["reported_balance"], Decimal("50.00"))

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
        self.assertEqual(metrics["expenses"], Decimal("0.00"))
        self.assertEqual(metrics["expense_count"], 0)
        self.assertTrue(metrics["employee_scope"])

    def test_activity_metrics_separate_product_and_service_revenue(self):
        service = Service.objects.create(
            activity=self.activity,
            name="Prestation test",
            slug="prestation-test-analytics",
            price=Decimal("15.00"),
        )
        sale = self.create_sale(
            self.employee,
            Decimal("35.00"),
            lines=[(Decimal("20.00"), Decimal("8.00"), 1, True)],
        )
        SaleLine.objects.create(
            sale=sale,
            service=service,
            quantity=1,
            unit_price=Decimal("15.00"),
            cost=Decimal("0.00"),
            margin_reliable=True,
            total=Decimal("15.00"),
        )

        metrics = dashboard_metrics(
            self.manager,
            self.activity,
            self.today,
            self.today,
        )

        self.assertEqual(metrics["revenue"], Decimal("35.00"))
        self.assertEqual(metrics["product_revenue"], Decimal("20.00"))
        self.assertEqual(metrics["service_revenue"], Decimal("15.00"))
        self.assertEqual(metrics["estimated_margin"], Decimal("12.00"))

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

    def test_global_item_rankings_separate_revenue_and_reliable_product_margin(self):
        global_user = User.objects.create_user("item-ranking-global", password="test")
        ActivityMembership.objects.create(user=global_user, role=Role.GLOBAL)
        product = Product.objects.create(
            activity=self.activity,
            name="Produit marge fiable",
            slug="produit-marge-fiable-classement",
            unit="pièce",
            price=Decimal("20.00"),
        )
        service = Service.objects.create(
            activity=self.activity,
            name="Prestation recette",
            slug="prestation-recette-classement",
            price=Decimal("50.00"),
        )
        sale = Sale.objects.create(
            activity=self.activity,
            user=self.employee,
            total=Decimal("70.00"),
        )
        SaleLine.objects.create(
            sale=sale,
            product=product,
            quantity=1,
            unit_price=Decimal("20.00"),
            cost=Decimal("8.00"),
            margin_reliable=True,
            total=Decimal("20.00"),
        )
        SaleLine.objects.create(
            sale=sale,
            service=service,
            quantity=1,
            unit_price=Decimal("50.00"),
            cost=Decimal("0.00"),
            margin_reliable=True,
            total=Decimal("50.00"),
        )

        rankings = global_item_metrics(global_user, self.today, self.today)

        best_seller = next(
            item for item in rankings["best_sellers"]
            if item["name"] == service.name
        )
        ranked_product = next(
            item for item in rankings["profitable_products"]
            if item["name"] == product.name
        )
        self.assertEqual(best_seller["revenue"], Decimal("50.00"))
        self.assertEqual(best_seller["kind"], "service")
        self.assertEqual(ranked_product["reliable_margin"], Decimal("12.00"))
        self.assertNotIn(
            service.name,
            [item["name"] for item in rankings["profitable_products"]],
        )

    def test_product_profitability_includes_unsold_items_and_only_reliable_margin(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Produit marge négative",
            slug="produit-marge-negative",
            unit="pièce",
            price=Decimal("5.00"),
            stock_quantity=4,
            average_cost=Decimal("8.00"),
        )
        unsold = Product.objects.create(
            activity=self.activity,
            name="Produit sans vente",
            slug="produit-sans-vente",
            unit="pièce",
            price=Decimal("12.00"),
            stock_quantity=7,
        )
        reliable_sale = self.create_sale(
            self.employee,
            Decimal("10.00"),
            lines=[(Decimal("5.00"), Decimal("8.00"), 2, True)],
        )
        SaleLine.objects.filter(sale=reliable_sale).update(product=product)
        unreliable_sale = self.create_sale(
            self.employee,
            Decimal("20.00"),
            lines=[(Decimal("10.00"), Decimal("4.00"), 2, False)],
        )
        SaleLine.objects.filter(sale=unreliable_sale).update(product=product)
        unknown_sale = self.create_sale(
            self.employee,
            Decimal("3.00"),
            lines=[(Decimal("3.00"), None, 1, False)],
        )
        SaleLine.objects.filter(sale=unknown_sale).update(product=product)
        canceled_sale = self.create_sale(
            self.employee,
            Decimal("100.00"),
            canceled=True,
            lines=[(Decimal("100.00"), Decimal("1.00"), 1, True)],
        )
        SaleLine.objects.filter(sale=canceled_sale).update(product=product)

        details = activity_operational_details(
            self.manager,
            self.activity,
            self.today,
            self.today,
        )
        rows = {row["product"].pk: row for row in details["product_profitability"]}
        product_row = rows[product.pk]

        self.assertEqual(product_row["quantity"], 5)
        self.assertEqual(product_row["revenue"], Decimal("33.00"))
        self.assertEqual(product_row["reliable_cogs"], Decimal("16.00"))
        self.assertEqual(product_row["reliable_margin"], Decimal("-6.00"))
        self.assertEqual(product_row["reliable_margin_rate"], Decimal("-60.00"))
        self.assertEqual(product_row["unknown_cost_line_count"], 1)
        self.assertEqual(product_row["unreliable_cost_line_count"], 1)
        self.assertEqual(product_row["last_sale_at"], unknown_sale.created_at)
        self.assertEqual(rows[unsold.pk]["quantity"], 0)
        self.assertIsNone(rows[unsold.pk]["reliable_margin"])

    def test_employee_product_profitability_is_scoped_to_own_sales(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Produit partagé",
            slug="produit-partage",
            unit="pièce",
            price=Decimal("10.00"),
            stock_quantity=10,
        )
        own_sale = self.create_sale(
            self.employee,
            Decimal("10.00"),
            lines=[(Decimal("10.00"), Decimal("4.00"), 1, True)],
        )
        SaleLine.objects.filter(sale=own_sale).update(product=product)
        other_sale = self.create_sale(
            self.manager,
            Decimal("90.00"),
            lines=[(Decimal("90.00"), Decimal("1.00"), 9, True)],
        )
        SaleLine.objects.filter(sale=other_sale).update(product=product)

        details = activity_operational_details(
            self.employee,
            self.activity,
            self.today,
            self.today,
        )

        product_row = next(
            row for row in details["product_profitability"]
            if row["product"].pk == product.pk
        )
        self.assertEqual(product_row["quantity"], 1)
        self.assertEqual(product_row["revenue"], Decimal("10.00"))
        self.assertEqual(product_row["reliable_margin"], Decimal("6.00"))
        self.assertEqual(product_row["last_sale_at"], own_sale.created_at)
