"""
Tests persistants JED-07 — module des ventes.

Couvre :
- ``create_sale`` (service central) : snapshots prix/coût, mouvements stock,
    rollback transactionnel, services (coût = 0), stock insuffisant.
- ``SaleLineForm`` / ``SaleLineFormSet`` : validation, lignes vides,
  produits+services simultanés, quantité.
- Vues (``SaleListView``, ``SaleCreateView``, ``SaleDetailView``) : flux web,
  permissions par activité (403 / 302), formulaire vide.
- ``SaleLine.margin`` (calcul de marge).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.catalog.models import Product, Service
from apps.inventory.models import StockMovement
from apps.inventory.services import record_stock_movement

from ..models import Sale, SaleCancellation, SaleLine
from ..forms import SaleLineForm, SaleLineFormSet
from ..services import cancel_sale, create_sale


class SaleModelTest(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Restaurant Test", slug="resto-test")
        self.user = User.objects.create_user("vendeur1", password="t123")
        ActivityMembership.objects.create(
            user=self.user, activity=self.activity, role=Role.MANAGER, is_active=True
        )
        self.product = Product.objects.create(
            activity=self.activity, name="Bière", slug="biere-t", unit="pièce",
            price=Decimal("2.50"), stock_quantity=100, average_cost=Decimal("1.00"),
        )

    def test_sale_str(self):
        sale = Sale.objects.create(activity=self.activity, user=self.user, total=Decimal("7.50"))
        self.assertIn(f"Ticket #{sale.pk}", str(sale))

    def test_sale_line_item_property_returns_product(self):
        sale = Sale.objects.create(activity=self.activity, user=self.user)
        line = SaleLine.objects.create(
            sale=sale, product=self.product, quantity=3,
            unit_price=Decimal("2.50"), cost=Decimal("1.00"), total=Decimal("7.50"),
        )
        self.assertEqual(line.item, self.product)

    def test_sale_line_item_property_returns_service(self):
        service = Service.objects.create(
            activity=self.activity, name="Cours", slug="cours-t", price=Decimal("30.00"),
        )
        sale = Sale.objects.create(activity=self.activity, user=self.user)
        line = SaleLine.objects.create(
            sale=sale, service=service, quantity=1,
            unit_price=Decimal("30.00"), cost=Decimal("0"), total=Decimal("30.00"),
        )
        self.assertEqual(line.item, service)

    def test_sale_line_margin(self):
        sale = Sale.objects.create(activity=self.activity, user=self.user)
        line = SaleLine.objects.create(
            sale=sale, product=self.product, quantity=3,
            unit_price=Decimal("2.50"), cost=Decimal("1.00"), total=Decimal("7.50"),
        )
        self.assertEqual(line.margin, Decimal("4.50"))

    def test_sale_line_clean_requires_product_or_service(self):
        sale = Sale.objects.create(activity=self.activity, user=self.user)
        line = SaleLine(sale=sale, quantity=1, unit_price=Decimal("2.50"))
        with self.assertRaises(ValidationError):
            line.full_clean()

    def test_sale_line_clean_rejects_both(self):
        service = Service.objects.create(
            activity=self.activity, name="S", slug="s-t", price=Decimal("10.00"),
        )
        sale = Sale.objects.create(activity=self.activity, user=self.user)
        line = SaleLine(sale=sale, product=self.product, service=service, quantity=1)
        with self.assertRaises(ValidationError):
            line.full_clean()


class CreateSaleServiceTest(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Restaurant Test", slug="resto-test")
        self.user = User.objects.create_user("vendeur1", password="t123")
        ActivityMembership.objects.create(
            user=self.user, activity=self.activity, role=Role.MANAGER, is_active=True
        )
        self.product = Product.objects.create(
            activity=self.activity, name="Bière", slug="biere-t", unit="pièce",
            price=Decimal("2.50"), stock_quantity=100, average_cost=Decimal("1.00"),
        )
        self.service = Service.objects.create(
            activity=self.activity, name="Cours cuisine", slug="cours-t", price=Decimal("30.00")
        )

    def test_create_sale_product_decrements_stock(self):
        sale = create_sale(self.activity, self.user, [{"item": self.product, "quantity": 3}])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 97)
        self.assertEqual(sale.total, Decimal("7.50"))
        self.assertEqual(sale.lines.first().unit_price, Decimal("2.50"))
        self.assertEqual(sale.lines.first().cost, Decimal("1.00"))
        self.assertTrue(sale.lines.first().margin_reliable)
        self.assertEqual(StockMovement.objects.filter(movement_type="EXIT").count(), 1)

    def test_create_sale_service_has_no_stock_movement(self):
        sale = create_sale(self.activity, self.user, [{"item": self.service, "quantity": 1}])
        self.assertEqual(sale.lines.first().cost, Decimal("0"))
        self.assertEqual(StockMovement.objects.filter(movement_type="EXIT").count(), 0)
        self.assertEqual(sale.total, Decimal("30.00"))

    def test_create_sale_mixed_lines(self):
        sale = create_sale(self.activity, self.user, [
            {"item": self.product, "quantity": 1},
            {"item": self.service, "quantity": 1},
            {"item": self.product, "quantity": 1},
        ])
        self.assertEqual(sale.total, Decimal("35.00"))
        self.assertEqual(sale.lines.count(), 3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 98)

    def test_create_sale_empty_lines_raises(self):
        with self.assertRaises(ValueError):
            create_sale(self.activity, self.user, [])

    def test_create_sale_invalid_item_raises(self):
        with self.assertRaises(ValueError):
            create_sale(self.activity, self.user, [{"item": "bad", "quantity": 1}])

    def test_create_sale_negative_quantity_raises(self):
        with self.assertRaises(ValueError):
            create_sale(self.activity, self.user, [{"item": self.product, "quantity": -1}])

    def test_create_sale_rejects_quantity_above_stock_without_changes(self):
        with self.assertRaisesRegex(ValidationError, "Stock insuffisant"):
            create_sale(self.activity, self.user, [{"item": self.product, "quantity": 150}])

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 100)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_create_sale_consuming_last_unit_keeps_margin_reliable(self):
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        sale = create_sale(self.activity, self.user, [{"item": self.product, "quantity": 1}])

        line = sale.lines.first()
        self.assertTrue(line.margin_reliable)
        self.assertEqual(line.cost, Decimal("1.00"))
        self.assertEqual(line.margin, Decimal("1.50"))

    def test_weighted_average_cost_and_sale_margin_match_audit_example(self):
        self.product.stock_quantity = 0
        self.product.average_cost = Decimal("0.00")
        self.product.price = Decimal("2000.00")
        self.product.save(update_fields=["stock_quantity", "average_cost", "price"])
        for quantity, unit_cost in ((10, Decimal("1000.00")), (10, Decimal("1500.00"))):
            record_stock_movement(
                product=self.product,
                movement_type=StockMovement.MovementType.ENTRY,
                quantity=quantity,
                unit_cost=unit_cost,
                user=self.user,
            )

        sale = create_sale(self.activity, self.user, [{"item": self.product, "quantity": 5}])
        line = sale.lines.get()

        self.assertEqual(self.product.average_cost, Decimal("1250.00"))
        self.assertEqual(sale.total, Decimal("10000.00"))
        self.assertEqual(line.cost * line.quantity, Decimal("6250.00"))
        self.assertEqual(line.margin, Decimal("3750.00"))
        self.assertEqual(line.margin / sale.total * 100, Decimal("37.5000"))

    def test_create_sale_rejects_combined_duplicate_lines_above_stock(self):
        self.product.stock_quantity = 3
        self.product.save(update_fields=["stock_quantity"])

        with self.assertRaises(ValidationError):
            create_sale(self.activity, self.user, [
                {"item": self.product, "quantity": 2},
                {"item": self.product, "quantity": 2},
            ])

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_negative_margin_is_preserved(self):
        self.product.stock_quantity = 1
        self.product.price = Decimal("0.50")
        self.product.save(update_fields=["stock_quantity", "price"])

        sale = create_sale(self.activity, self.user, [{"item": self.product, "quantity": 1}])

        line = sale.lines.first()
        self.assertTrue(line.margin_reliable)
        self.assertEqual(line.margin, Decimal("-0.50"))

    def test_zero_cost_without_purchase_history_is_unknown(self):
        self.product.stock_quantity = 2
        self.product.average_cost = Decimal("0.00")
        self.product.save(update_fields=["stock_quantity", "average_cost"])

        sale = create_sale(self.activity, self.user, [{"item": self.product, "quantity": 1}])

        line = sale.lines.first()
        self.assertIsNone(line.cost)
        self.assertIsNone(line.margin)
        self.assertFalse(line.margin_reliable)

    def test_zero_average_cost_with_positive_purchase_history_is_unknown(self):
        self.product.average_cost = Decimal("0.00")
        self.product.save(update_fields=["average_cost"])
        StockMovement.objects.create(
            product=self.product,
            movement_type=StockMovement.MovementType.ENTRY,
            quantity=1,
            unit_cost=Decimal("1.00"),
            user=self.user,
            activity=self.activity,
        )

        sale = create_sale(self.activity, self.user, [{"item": self.product, "quantity": 1}])

        line = sale.lines.get()
        self.assertIsNone(line.cost)
        self.assertIsNone(line.margin)
        self.assertFalse(line.margin_reliable)

    def test_create_sale_rejects_item_from_another_activity(self):
        other_activity = Activity.objects.create(name="Salon", slug="salon-other")
        other_product = Product.objects.create(
            activity=other_activity,
            name="Shampoo",
            slug="shampoo-other",
            unit="bottle",
            price=Decimal("8.00"),
            stock_quantity=5,
            average_cost=Decimal("3.00"),
        )
        other_service = Service.objects.create(
            activity=other_activity,
            name="Coupe",
            slug="coupe-other",
            price=Decimal("20.00"),
        )

        for item in (other_product, other_service):
            with self.subTest(item=item):
                with self.assertRaisesRegex(ValueError, "appartenir"):
                    create_sale(self.activity, self.user, [{"item": item, "quantity": 1}])

        other_product.refresh_from_db()
        self.assertEqual(other_product.stock_quantity, 5)
        self.assertEqual(Sale.objects.count(), 0)

    def test_create_sale_price_change_does_not_affect_existing(self):
        sale = create_sale(self.activity, self.user, [{"item": self.product, "quantity": 3}])
        self.product.price = Decimal("4.00")
        self.product.save()
        sale.refresh_from_db()
        self.assertEqual(sale.lines.first().unit_price, Decimal("2.50"))

    def test_create_sale_rollback_on_error(self):
        before = Sale.objects.count()
        with self.assertRaises(ValueError):
            create_sale(self.activity, self.user, [
                {"item": self.product, "quantity": 1},
                {"item": "bad", "quantity": 1},
            ])
        self.assertEqual(Sale.objects.count(), before)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 100)


class CancelSaleServiceTest(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Shop", slug="cancel-shop")
        self.user = User.objects.create_user("seller-cancel", password="t123")
        ActivityMembership.objects.create(
            user=self.user, activity=self.activity, role=Role.EMPLOYEE
        )
        self.product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="soap-cancel",
            unit="piece",
            price=Decimal("5.00"),
            stock_quantity=10,
            average_cost=Decimal("2.00"),
        )
        self.service = Service.objects.create(
            activity=self.activity,
            name="Consultation",
            slug="consult-cancel",
            price=Decimal("20.00"),
        )
        self.sale = create_sale(
            self.activity,
            self.user,
            [
                {"item": self.product, "quantity": 2},
                {"item": self.service, "quantity": 1},
            ],
        )

    def test_cancellation_restores_product_stock_once_and_keeps_sale(self):
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

        cancellation = cancel_sale(self.sale, self.user, "Saisie en double")
        repeated = cancel_sale(self.sale, self.user, "Autre motif")

        self.product.refresh_from_db()
        self.sale.refresh_from_db()
        self.assertEqual(cancellation.pk, repeated.pk)
        self.assertTrue(self.sale.is_canceled)
        self.assertEqual(self.sale.lines.count(), 2)
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(
            StockMovement.objects.filter(
                product=self.product,
                movement_type=StockMovement.MovementType.CORRECTION,
            ).count(),
            1,
        )
        self.assertEqual(cancellation.user, self.user)
        self.assertEqual(cancellation.reason, "Saisie en double")

    def test_cancellation_requires_nonblank_reason(self):
        with self.assertRaises(ValidationError):
            cancel_sale(self.sale, self.user, "   ")
        self.assertFalse(self.sale.is_canceled)

    def test_employee_cannot_cancel_another_users_sale(self):
        colleague = User.objects.create_user("colleague-cancel", password="t123")
        ActivityMembership.objects.create(
            user=colleague, activity=self.activity, role=Role.EMPLOYEE
        )

        with self.assertRaises(ValidationError):
            cancel_sale(self.sale, colleague, "Not my sale")

        self.assertFalse(self.sale.is_canceled)

    def test_failed_stock_restoration_rolls_back_cancellation(self):
        from unittest.mock import patch

        with patch(
            "apps.inventory.services.record_stock_movement",
            side_effect=RuntimeError("stock movement failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "stock movement failed"):
                cancel_sale(self.sale, self.user, "Rollback test")

        self.assertFalse(SaleCancellation.objects.filter(sale=self.sale).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)


class SaleLineFormTest(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Restaurant Test", slug="resto-test")
        self.product = Product.objects.create(
            activity=self.activity, name="Bière", slug="biere-t", unit="pièce",
            price=Decimal("2.50"), stock_quantity=100, average_cost=Decimal("1.00"),
        )
        self.service = Service.objects.create(
            activity=self.activity, name="Cours", slug="cours-t", price=Decimal("30.00")
        )

    def test_form_accepts_product(self):
        form = SaleLineForm(
            data={"product": self.product.pk, "service": "", "quantity": 2},
            activity=self.activity
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_does_not_offer_product_with_zero_stock(self):
        unavailable = Product.objects.create(
            activity=self.activity,
            name="Épuisé",
            slug="epuise-t",
            unit="pièce",
            price=Decimal("1.00"),
            stock_quantity=0,
        )

        form = SaleLineForm(activity=self.activity)

        self.assertNotIn(unavailable, form.fields["product"].queryset)
        self.assertNotIn(f"product:{unavailable.pk}", [value for value, _ in form.fields["item"].choices])

    def test_form_rejects_quantity_above_available_stock(self):
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        form = SaleLineForm(
            data={"item": f"product:{self.product.pk}", "quantity": 2},
            activity=self.activity,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Stock insuffisant", str(form.errors))

    def test_form_accepts_service(self):
        form = SaleLineForm(
            data={"product": "", "service": self.service.pk, "quantity": 1},
            activity=self.activity
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_both(self):
        form = SaleLineForm(
            data={"product": self.product.pk, "service": self.service.pk, "quantity": 1},
            activity=self.activity
        )
        self.assertFalse(form.is_valid())

    def test_formset_requires_at_least_one_line(self):
        formset = SaleLineFormSet(
            data={
                "form-TOTAL_FORMS": "3",
                "form-INITIAL_FORMS": "0",
                "form-0-product": "", "form-0-service": "", "form-0-quantity": "1",
                "form-1-product": "", "form-1-service": "", "form-1-quantity": "1",
                "form-2-product": "", "form-2-service": "", "form-2-quantity": "1",
            },
            form_kwargs={"activity": self.activity},
            prefix="form",
        )
        self.assertFalse(formset.is_valid())
        self.assertTrue(formset.non_form_errors())
        self.assertIn("au moins un", str(formset.non_form_errors()))

    def test_formset_accepts_valid_lines(self):
        formset = SaleLineFormSet(
            data={
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-0-product": str(self.product.pk),
                "form-0-service": "",
                "form-0-quantity": "2",
                "form-1-product": "",
                "form-1-service": str(self.service.pk),
                "form-1-quantity": "1",
            },
            form_kwargs={"activity": self.activity},
            prefix="form",
        )
        self.assertTrue(formset.is_valid(), formset.errors)


class SaleViewsTest(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Restaurant Test", slug="resto-test")
        self.other_activity = Activity.objects.create(name="Coiffure Test", slug="coiffure-test")
        self.global_user = User.objects.create_user("global1", password="t123")
        ActivityMembership.objects.create(
            user=self.global_user, activity=None, role=Role.GLOBAL, is_active=True
        )
        self.manager = User.objects.create_user("mgr1", password="t123")
        ActivityMembership.objects.create(
            user=self.manager, activity=self.activity, role=Role.MANAGER, is_active=True
        )
        self.employee = User.objects.create_user("emp1", password="t123")
        ActivityMembership.objects.create(
            user=self.employee, activity=self.activity, role=Role.EMPLOYEE, is_active=True
        )
        self.outsider_employee = User.objects.create_user("emp2", password="t123")
        ActivityMembership.objects.create(
            user=self.outsider_employee, activity=self.other_activity, role=Role.EMPLOYEE, is_active=True
        )
        self.product = Product.objects.create(
            activity=self.activity, name="Bière", slug="biere-t", unit="pièce",
            price=Decimal("2.50"), stock_quantity=100, average_cost=Decimal("1.00"),
        )
        self.service = Service.objects.create(
            activity=self.activity, name="Cours", slug="cours-t", price=Decimal("30.00")
        )

    def _post_data(self, product=None, service=None, qty=1):
        data = {"form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0"}
        pid = str(product.pk) if product else ""
        sid = str(service.pk) if service else ""
        data.update({
            "form-0-product": pid, "form-0-service": sid, "form-0-quantity": str(qty)
        })
        return data

    def test_global_user_can_access_views(self):
        self.client.force_login(self.global_user)
        url = reverse("sales:sale_list", kwargs={"activity_slug": self.activity.slug})
        self.assertEqual(self.client.get(url).status_code, 200)
        add_url = reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug})
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Produit ou prestation")
        self.assertContains(response, "stock 100")
        self.assertContains(response, "sale-stock-data")
        self.assertContains(response, "Ajouter un article")

    def test_global_user_can_create_sale(self):
        self.client.force_login(self.global_user)
        add_url = reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug})
        r = self.client.post(add_url, self._post_data(product=self.product, qty=2))
        self.assertEqual(r.status_code, 302)
        sale = Sale.objects.get()
        self.assertEqual(sale.total, Decimal("5.00"))
        self.assertEqual(sale.user, self.global_user)
        expected = reverse("sales:sale_detail",
                           kwargs={"activity_slug": self.activity.slug, "pk": sale.pk})
        self.assertEqual(r.url, expected)

    def test_employee_cannot_access_other_activity(self):
        self.client.force_login(self.outsider_employee)
        add_url = reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug})
        self.assertEqual(self.client.get(add_url).status_code, 403)
        list_url = reverse("sales:sale_list", kwargs={"activity_slug": self.activity.slug})
        self.assertEqual(self.client.get(list_url).status_code, 403)

    def test_employee_can_create_sale_on_own_activity(self):
        self.client.force_login(self.employee)
        add_url = reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug})
        r = self.client.post(add_url, self._post_data(service=self.service, qty=1))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Sale.objects.count(), 1)

    def test_employee_can_create_sale_with_single_item_selector(self):
        self.client.force_login(self.employee)
        response = self.client.post(
            reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug}),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-0-item": f"product:{self.product.pk}",
                "form-0-quantity": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        sale = Sale.objects.get()
        self.assertEqual(sale.total, Decimal("5.00"))
        self.assertEqual(sale.lines.get().product, self.product)

    def test_single_item_selector_rejects_product_from_another_activity(self):
        self.client.force_login(self.employee)
        other_product = Product.objects.create(
            activity=self.other_activity,
            name="Produit privé",
            slug="produit-prive",
            unit="pièce",
            price=Decimal("20.00"),
            stock_quantity=5,
            average_cost=Decimal("10.00"),
        )
        response = self.client.post(
            reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug}),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-0-item": f"product:{other_product.pk}",
                "form-0-quantity": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertContains(response, "Choisir un article", status_code=200)

    def test_employee_sale_list_only_contains_own_sales(self):
        create_sale(self.activity, self.global_user, [
            {"item": self.product, "quantity": 1}
        ])
        own_sale = create_sale(self.activity, self.employee, [
            {"item": self.service, "quantity": 1}
        ])
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse("sales:sale_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["sales"]), [own_sale])

    def test_manager_sale_list_includes_employees_sales(self):
        sale = create_sale(self.activity, self.employee, [
            {"item": self.service, "quantity": 1}
        ])
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("sales:sale_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["sales"]), [sale])

    def test_employee_cannot_open_colleague_sale_in_same_activity(self):
        sale = create_sale(self.activity, self.global_user, [
            {"item": self.product, "quantity": 1}
        ])
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse(
                "sales:sale_detail",
                kwargs={"activity_slug": self.activity.slug, "pk": sale.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_superuser_has_global_activity_access(self):
        superuser = User.objects.create_superuser(
            "root", email="root@example.test", password="t123"
        )
        self.client.force_login(superuser)

        response = self.client.get(
            reverse("sales:sale_list", kwargs={"activity_slug": self.other_activity.slug})
        )

        self.assertEqual(response.status_code, 200)

    def test_superuser_can_manage_any_activity(self):
        superuser = User.objects.create_superuser(
            "root", email="root@example.test", password="t123"
        )
        self.client.force_login(superuser)

        response = self.client.get(
            reverse("accounts:activity_manage", kwargs={"activity_slug": self.other_activity.slug})
        )

        self.assertEqual(response.status_code, 200)

    def test_empty_formset_returns_200_with_message(self):
        self.client.force_login(self.manager)
        add_url = reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug})
        r = self.client.post(add_url, {
            "form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0",
            "form-0-product": "", "form-0-service": "", "form-0-quantity": "1",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "au moins", status_code=200)
        self.assertEqual(Sale.objects.count(), 0)

    def test_detail_view(self):
        sale = create_sale(self.activity, self.global_user, [
            {"item": self.product, "quantity": 2}
        ])
        self.client.force_login(self.global_user)
        detail_url = reverse("sales:sale_detail",
                             kwargs={"activity_slug": self.activity.slug, "pk": sale.pk})
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "5,00 FCFA")
        self.assertContains(r, "3,00 FCFA")

    def test_detail_view_rejects_sale_when_stock_is_zero(self):
        self.product.stock_quantity = 0
        self.product.save(update_fields=["stock_quantity"])
        self.client.force_login(self.global_user)

        response = self.client.post(
            reverse("sales:sale_add", kwargs={"activity_slug": self.activity.slug}),
            self._post_data(product=self.product, qty=1),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sale.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)

    def test_detail_view_403_for_other_activity_employee(self):
        sale = create_sale(self.activity, self.global_user, [
            {"item": self.product, "quantity": 1}
        ])
        self.client.force_login(self.outsider_employee)
        detail_url = reverse("sales:sale_detail",
                             kwargs={"activity_slug": self.activity.slug, "pk": sale.pk})
        self.assertEqual(self.client.get(detail_url).status_code, 403)


class SaleCancellationViewsTest(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Shop", slug="cancel-view-shop")
        self.other_activity = Activity.objects.create(name="Salon", slug="cancel-view-salon")
        self.employee = User.objects.create_user("cancel-employee", password="t123")
        ActivityMembership.objects.create(
            user=self.employee, activity=self.activity, role=Role.EMPLOYEE
        )
        self.colleague = User.objects.create_user("cancel-colleague", password="t123")
        ActivityMembership.objects.create(
            user=self.colleague, activity=self.activity, role=Role.EMPLOYEE
        )
        self.manager = User.objects.create_user("cancel-manager", password="t123")
        ActivityMembership.objects.create(
            user=self.manager, activity=self.activity, role=Role.MANAGER
        )
        self.outsider = User.objects.create_user("cancel-outsider", password="t123")
        ActivityMembership.objects.create(
            user=self.outsider, activity=self.other_activity, role=Role.EMPLOYEE
        )
        self.product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="cancel-view-soap",
            unit="piece",
            price=Decimal("5.00"),
            stock_quantity=8,
            average_cost=Decimal("2.00"),
        )
        self.sale = create_sale(
            self.activity, self.employee, [{"item": self.product, "quantity": 2}]
        )

    def cancel_url(self, sale=None):
        return reverse(
            "sales:sale_cancel",
            kwargs={"activity_slug": self.activity.slug, "pk": (sale or self.sale).pk},
        )

    def test_employee_can_cancel_own_sale_with_reason(self):
        self.client.force_login(self.employee)

        response = self.client.post(self.cancel_url(), {"reason": "Ticket en double"})

        cancellation = SaleCancellation.objects.get(sale=self.sale)
        self.assertRedirects(
            response,
            reverse(
                "sales:sale_cancellation_detail",
                kwargs={"activity_slug": self.activity.slug, "pk": cancellation.pk},
            ),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_blank_reason_is_rejected_without_cancelling(self):
        self.client.force_login(self.employee)

        response = self.client.post(self.cancel_url(), {"reason": "  "})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SaleCancellation.objects.filter(sale=self.sale).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 6)

    def test_repeated_post_does_not_restore_stock_twice(self):
        self.client.force_login(self.employee)
        url = self.cancel_url()

        self.client.post(url, {"reason": "Ticket en double"})
        self.client.post(url, {"reason": "Repetition"})

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)
        self.assertEqual(SaleCancellation.objects.filter(sale=self.sale).count(), 1)
        self.assertEqual(
            StockMovement.objects.filter(
                product=self.product,
                movement_type=StockMovement.MovementType.CORRECTION,
            ).count(),
            1,
        )

    def test_employee_cannot_cancel_colleagues_sale(self):
        colleague_sale = create_sale(
            self.activity, self.colleague, [{"item": self.product, "quantity": 1}]
        )
        self.client.force_login(self.employee)

        response = self.client.get(self.cancel_url(colleague_sale))

        self.assertEqual(response.status_code, 403)

    def test_manager_can_cancel_sale_in_activity(self):
        self.client.force_login(self.manager)

        response = self.client.post(self.cancel_url(), {"reason": "Erreur de saisie"})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SaleCancellation.objects.filter(sale=self.sale, user=self.manager).exists())

    def test_employee_cancellation_journal_is_limited_to_own_sales(self):
        colleague_sale = create_sale(
            self.activity, self.colleague, [{"item": self.product, "quantity": 1}]
        )
        cancel_sale(self.sale, self.employee, "Mon ticket")
        cancel_sale(colleague_sale, self.colleague, "Ticket collègue")
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse("sales:sale_cancellation_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["cancellations"].values_list("sale_id", flat=True)), [self.sale.pk])

    def test_outsider_cannot_read_activity_cancellation_journal(self):
        self.client.force_login(self.outsider)

        response = self.client.get(
            reverse("sales:sale_cancellation_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 403)




