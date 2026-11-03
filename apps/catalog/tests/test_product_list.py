from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity
from apps.catalog.models import PriceHistory, Product
from apps.inventory.models import StockMovement


class ProductListViewTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Boutique cartes", slug="boutique-cartes")
        self.manager = User.objects.create_user("manager", password="test-password")
        ActivityMembership.objects.create(
            user=self.manager,
            activity=self.activity,
            role=Role.MANAGER,
        )
        self.product = Product.objects.create(
            activity=self.activity,
            name="Huile de palme",
            slug="huile-de-palme",
            unit="bouteille",
            price=Decimal("2500.00"),
            average_cost=Decimal("1800.00"),
            stock_quantity=4,
        )
        self.product_without_cost = Product.objects.create(
            activity=self.activity,
            name="Savon",
            slug="savon",
            unit="pièce",
            price=Decimal("500.00"),
        )
        self.product_with_zero_cost = Product.objects.create(
            activity=self.activity,
            name="Eau",
            slug="eau",
            unit="bouteille",
            price=Decimal("350.00"),
        )
        StockMovement.objects.create(
            product=self.product_with_zero_cost,
            activity=self.activity,
            movement_type=StockMovement.MovementType.ENTRY,
            quantity=1,
            unit_cost=Decimal("0.00"),
            user=self.manager,
        )

    def test_product_cards_prioritize_name_and_purchase_and_sale_prices(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("catalog:product_list", args=[self.activity.slug])
        )
        rendered_page = response.content.decode().replace("\xa0", " ")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Huile de palme")
        self.assertContains(response, "Par bouteille")
        self.assertContains(response, "Achat / unité")
        self.assertIn("1 800 <span>FCFA</span>", rendered_page)
        self.assertContains(response, "Vente / unité")
        self.assertIn("2 500 <span>FCFA</span>", rendered_page)
        self.assertContains(response, "<strong>0 <span>FCFA</span></strong>", html=True)
        self.assertContains(response, "Non renseigné")
        self.assertNotContains(response, "Modifié le")
        self.assertNotContains(response, "Statut")

    def test_create_product_generates_unique_slug_and_defaults_to_active(self):
        self.client.force_login(self.manager)
        create_url = reverse("catalog:product_add", args=[self.activity.slug])
        product_data = {
            "name": "Café Touba",
            "unit": "tasse",
            "price": "300",
            "description": "",
        }

        response = self.client.post(create_url, product_data)
        self.assertRedirects(
            response,
            reverse("catalog:product_list", args=[self.activity.slug]),
        )
        first_product = Product.objects.get(name="Café Touba")
        self.assertEqual(first_product.slug, "cafe-touba")
        self.assertTrue(first_product.is_active)

        response = self.client.post(create_url, product_data)
        self.assertRedirects(
            response,
            reverse("catalog:product_list", args=[self.activity.slug]),
        )
        second_product = Product.objects.get(name="Café Touba", slug="cafe-touba-2")
        self.assertTrue(second_product.is_active)

    def test_create_form_hides_slug_and_active_fields(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("catalog:product_add", args=[self.activity.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="unit"')
        self.assertContains(response, 'name="price"')
        self.assertNotContains(response, 'name="slug"')
        self.assertNotContains(response, 'name="is_active"')

    def test_edit_product_saves_fields_keeps_slug_and_updates_price_history(self):
        self.client.force_login(self.manager)
        edit_url = reverse(
            "catalog:product_edit",
            kwargs={"activity_slug": self.activity.slug, "slug": self.product.slug},
        )

        get_response = self.client.get(edit_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'name="is_active"')
        self.assertNotContains(get_response, 'name="slug"')

        response = self.client.post(
            edit_url,
            {
                "name": "Huile de palme raffinée",
                "unit": "bidon",
                "description": "Conditionnement familial",
                "price": "3000.00",
                "is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("catalog:product_list", args=[self.activity.slug]),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Huile de palme raffinée")
        self.assertEqual(self.product.slug, "huile-de-palme")
        self.assertEqual(self.product.unit, "bidon")
        self.assertEqual(self.product.description, "Conditionnement familial")
        self.assertEqual(self.product.price, Decimal("3000.00"))
        self.assertTrue(self.product.is_active)
        self.assertEqual(
            list(PriceHistory.objects.filter(object_id=self.product.pk).values_list("price", flat=True)),
            [Decimal("3000.00"), Decimal("2500.00")],
        )