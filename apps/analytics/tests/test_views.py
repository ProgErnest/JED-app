from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
        self.assertContains(response, "Marge estimée des produits")
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
        self.assertEqual(response.context["totals"]["revenue"], Decimal("1250.00"))
        self.assertEqual(response.context["totals"]["stock_purchases"], Decimal("360.00"))
        self.assertEqual(response.context["period"], "day")
        employee_summary = next(
            row for row in response.context["employees"]
            if row["username"] == "view-global"
        )
        self.assertEqual(employee_summary["sale_count"], 1)
        self.assertEqual(employee_summary["revenue"], Decimal("1250.00"))
        self.assertEqual(employee_summary["stock_purchases"], Decimal("360.00"))
        cancellation = SaleCancellation.objects.get(sale=old_sale)
        self.assertEqual(employee_summary["last_operation"], cancellation.created_at)
        activity_summary = next(
            row for row in response.context["rows"]
            if row["activity"] == self.activity
        )
        self.assertEqual(activity_summary["stock_purchases"], Decimal("360.00"))
        self.assertContains(response, "Employés les plus actifs")
        self.assertContains(response, "Meilleures ventes")
        self.assertContains(response, "Marge des produits")
        self.assertContains(response, "Achats de stock")
        self.assertNotContains(response, "Dépenses déclarées")
        self.assertContains(response, "view-global")
        self.assertNotContains(response, f"Annulation de la vente #{old_sale.pk}")
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

    def test_global_period_presets_use_calendar_boundaries(self):
        global_user = User.objects.create_user("period-global", password="test")
        ActivityMembership.objects.create(user=global_user, role=Role.GLOBAL)
        self.client.force_login(global_user)

        today = timezone.localdate()
        for period, expected_start, expected_previous_start, expected_previous_end in (
            ("day", today, today - timedelta(days=1), today - timedelta(days=1)),
            (
                "week",
                today - timedelta(days=today.weekday()),
                today - timedelta(days=today.weekday() + 7),
                today - timedelta(days=7),
            ),
            (
                "month",
                today.replace(day=1),
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
                (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                + timedelta(days=today.day - 1),
            ),
        ):
            response = self.client.get(
                reverse("analytics:global-dashboard"),
                {"period": period},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["period"], period)
            self.assertEqual(response.context["start_date"], expected_start)
            self.assertEqual(response.context["end_date"], today)
            self.assertEqual(response.context["previous_start"], expected_previous_start)
            self.assertEqual(response.context["previous_end"], expected_previous_end)

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

    def test_activity_dashboard_labels_sales_and_margin_indicators_clearly(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Produit tableau indicateurs",
            slug="produit-tableau-indicateurs",
            unit="pièce",
            price=Decimal("20.00"),
        )
        sale = Sale.objects.create(
            activity=self.activity,
            user=self.manager,
            total=Decimal("20.00"),
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
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("analytics:activity-dashboard", args=[self.activity.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total des ventes")
        self.assertContains(response, "Ventes de produits")
        self.assertContains(response, "Ventes de prestations")
        self.assertContains(response, "Évolution des ventes")
        self.assertContains(response, "60,00 %")
        self.assertNotContains(response, "Dépenses par catégorie")
