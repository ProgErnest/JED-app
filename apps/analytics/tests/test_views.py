from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.analytics.services import dashboard_metrics
from apps.expenses.models import ExpenseCategory
from apps.expenses.models import Expense
from apps.catalog.models import Product
from apps.inventory.models import StockMovement
from apps.sales.models import Sale, SaleCancellation, SaleLine


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

    def test_mobile_navigation_uses_wrapping_layout(self):
        css_path = Path(__file__).resolve().parents[3] / "static" / "css" / "jed.css"
        css = css_path.read_text(encoding="utf-8")

        self.assertIn(".site-nav { order: 3; width: 100%; flex-wrap: wrap; overflow: visible;", css)

    def test_user_without_activity_access_is_denied(self):
        unrelated = User.objects.create_user("unrelated", password="test")
        self.client.force_login(unrelated)
        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )
        self.assertEqual(response.status_code, 403)

    def test_employee_can_view_own_activity_dashboard(self):
        colleague = User.objects.create_user("view-colleague", password="test")
        Sale.objects.create(
            activity=self.activity,
            user=colleague,
            total=Decimal("75.00"),
        )
        Sale.objects.create(
            activity=self.activity,
            user=self.employee,
            total=Decimal("25.00"),
        )
        self.client.force_login(self.employee)
        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vos opérations uniquement")
        self.assertContains(response, "Marge brute estimée")
        self.assertEqual(len(response.context["sales"]), 1)
        self.assertEqual(response.context["sales"][0].user, self.employee)
        self.assertNotContains(response, "view-colleague")

    def test_global_dashboard_is_for_global_role_only(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("analytics:global-dashboard"))
        self.assertEqual(response.status_code, 403)

        global_user = User.objects.create_user("view-global", password="test")
        ActivityMembership.objects.create(user=global_user, role=Role.GLOBAL)
        Sale.objects.create(
            activity=self.activity,
            user=global_user,
            total=Decimal("1250.00"),
        )
        category = ExpenseCategory.objects.create(
            activity=self.activity,
            name="Transport global",
            slug="transport-global-dashboard",
        )
        Expense.objects.create(
            activity=self.activity,
            category=category,
            user=global_user,
            amount=Decimal("200.00"),
        )
        product = Product.objects.create(
            activity=self.activity,
            name="Huile tableau global",
            slug="huile-tableau-global",
            unit="litre",
            price=Decimal("500.00"),
        )
        StockMovement.objects.create(
            product=product,
            activity=self.activity,
            user=global_user,
            movement_type=StockMovement.MovementType.ENTRY,
            quantity=3,
            unit_cost=Decimal("120.00"),
            reason="Réapprovisionnement",
        )
        old_sale = Sale.objects.create(
            activity=self.activity,
            user=self.employee,
            total=Decimal("400.00"),
        )
        Sale.objects.filter(pk=old_sale.pk).update(
            created_at=old_sale.created_at.replace(year=old_sale.created_at.year - 1)
        )
        SaleCancellation.objects.create(
            sale=old_sale,
            user=global_user,
            reason="Erreur de saisie",
        )
        self.client.force_login(global_user)
        response = self.client.get(reverse("analytics:global-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.activity.name)
        self.assertEqual(response.context["today_totals"]["revenue"], Decimal("1250.00"))
        self.assertEqual(response.context["today_totals"]["expenses"], Decimal("200.00"))
        self.assertEqual(response.context["today_totals"]["reported_balance"], Decimal("1050.00"))
        self.assertEqual(response.context["today_totals"]["stock_purchases"], Decimal("360.00"))
        employee_summary = next(
            row for row in response.context["employees"]
            if row["username"] == "view-global"
        )
        self.assertEqual(employee_summary["sale_count"], 1)
        self.assertEqual(employee_summary["revenue"], Decimal("1250.00"))
        self.assertEqual(employee_summary["expense_count"], 1)
        self.assertEqual(employee_summary["expenses"], Decimal("200.00"))
        self.assertEqual(employee_summary["stock_purchases"], Decimal("360.00"))
        cancellation = SaleCancellation.objects.get(sale=old_sale)
        self.assertEqual(employee_summary["last_operation"], cancellation.created_at)
        activity_summary = next(
            row for row in response.context["rows"]
            if row["activity"] == self.activity
        )
        self.assertEqual(activity_summary["stock_purchases"], Decimal("360.00"))
        self.assertContains(response, "Dernières opérations")
        self.assertContains(response, "Activité des employés")
        self.assertContains(response, "Achats de stock")
        self.assertContains(response, "view-global")
        self.assertContains(response, f"Annulation de la vente #{old_sale.pk}")
        self.assertContains(
            response,
            reverse("sales:sale_list", args=[self.activity.slug]),
        )

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

    def test_activity_dashboard_renders_unsold_product_and_negative_margin(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Article déficitaire",
            slug="article-deficitaire",
            unit="pièce",
            price=Decimal("5.00"),
            stock_quantity=3,
        )
        unsold = Product.objects.create(
            activity=self.activity,
            name="Article jamais vendu",
            slug="article-jamais-vendu",
            unit="pièce",
            price=Decimal("12.00"),
            stock_quantity=4,
        )
        sale = Sale.objects.create(
            activity=self.activity,
            user=self.manager,
            total=Decimal("5.00"),
        )
        SaleLine.objects.create(
            sale=sale,
            product=product,
            quantity=1,
            unit_price=Decimal("5.00"),
            cost=Decimal("8.00"),
            margin_reliable=True,
            total=Decimal("5.00"),
        )
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rentabilité et rotation des produits")
        self.assertContains(response, product.name)
        self.assertContains(response, "-3,00 FCFA")
        self.assertContains(response, unsold.name)
        product_rows = {
            row["product"].pk: row for row in response.context["product_profitability"]
        }
        self.assertEqual(product_rows[unsold.pk]["quantity"], 0)
        self.assertIsNone(product_rows[unsold.pk]["reliable_margin"])
