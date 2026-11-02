from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity
from apps.catalog.models import Product
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