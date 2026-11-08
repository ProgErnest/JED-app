from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity
from apps.catalog.models import CatalogCategory, Product, Service
from apps.catalog.services import load_reference_catalog
from apps.inventory.models import StockMovement
from apps.sales.models import Sale, SaleLine


class CatalogCategoryTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Boutique test", slug="boutique-test")
        self.other_activity = Activity.objects.create(name="Salon test", slug="salon-test")
        self.manager = User.objects.create_user("category-manager", password="test-password")
        ActivityMembership.objects.create(
            user=self.manager, activity=self.activity, role=Role.MANAGER
        )
        self.employee = User.objects.create_user("category-employee", password="test-password")
        ActivityMembership.objects.create(
            user=self.employee, activity=self.activity, role=Role.EMPLOYEE
        )
        self.category = CatalogCategory.objects.create(
            activity=self.activity, name="Boissons", slug="boissons"
        )

    def test_category_form_is_limited_to_activity(self):
        Product.objects.create(
            activity=self.other_activity,
            category=CatalogCategory.objects.create(
                activity=self.other_activity, name="Autres", slug="autres"
            ),
            name="Eau",
            slug="eau-autre",
            unit="bouteille",
            price=Decimal("250"),
        )
        from apps.catalog.forms import ProductForm

        form = ProductForm(
            data={"name": "Soda", "unit": "bouteille", "price": "500", "category": "1"},
            activity=self.activity,
        )
        self.assertNotIn(
            Product.objects.first().category_id,
            form.fields["category"].queryset.values_list("pk", flat=True),
        )

    def test_model_rejects_category_from_another_activity(self):
        product = Product(
            activity=self.activity,
            category=CatalogCategory.objects.create(
                activity=self.other_activity, name="Snacks", slug="snacks"
            ),
            name="Eau",
            slug="eau-cross-category",
            unit="bouteille",
            price=Decimal("250"),
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_manager_can_create_category_and_employee_cannot(self):
        self.client.force_login(self.manager)
        create_url = reverse("catalog:category_add", args=[self.activity.slug])
        response = self.client.post(create_url, {"name": "Snacks", "sort_order": "1"})
        self.assertRedirects(
            response, reverse("catalog:category_list", args=[self.activity.slug])
        )
        created = CatalogCategory.objects.get(activity=self.activity, name="Snacks")
        self.assertEqual(created.slug, "snacks")

        self.client.force_login(self.employee)
        response = self.client.post(
            create_url, {"name": "Interdit", "sort_order": "2"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CatalogCategory.objects.filter(name="Interdit").exists())

    def test_product_and_service_lists_filter_by_category_and_unclassified(self):
        Product.objects.create(
            activity=self.activity,
            category=self.category,
            name="Eau",
            slug="eau",
            unit="bouteille",
            price=Decimal("250"),
        )
        Service.objects.create(
            activity=self.activity,
            category=self.category,
            name="Livraison",
            slug="livraison",
            price=Decimal("500"),
        )
        Product.objects.create(
            activity=self.activity,
            name="Riz",
            slug="riz",
            unit="sac",
            price=Decimal("2500"),
        )
        self.client.force_login(self.manager)

        product_response = self.client.get(
            reverse("catalog:product_list", args=[self.activity.slug]),
            {"category": "none"},
        )
        service_response = self.client.get(
            reverse("catalog:service_list", args=[self.activity.slug]),
            {"category": str(self.category.pk)},
        )
        self.assertContains(product_response, "Riz")
        self.assertNotContains(product_response, "Eau")
        self.assertContains(service_response, "Livraison")
        self.assertContains(service_response, "Boissons")

    def test_inactive_category_remains_on_existing_item_edit_and_sale_catalog(self):
        self.category.is_active = False
        self.category.save(update_fields=["is_active"])
        product = Product.objects.create(
            activity=self.activity,
            category=self.category,
            name="Eau minérale",
            slug="eau-minerale",
            unit="bouteille",
            price=Decimal("300"),
            stock_quantity=5,
        )
        self.client.force_login(self.manager)
        edit_url = reverse(
            "catalog:product_edit",
            kwargs={"activity_slug": self.activity.slug, "slug": product.slug},
        )
        self.assertEqual(self.client.get(edit_url).status_code, 200)
        sale_url = reverse("sales:sale_add", args=[self.activity.slug])
        response = self.client.get(sale_url)
        self.assertContains(response, f'data-item-category="{self.category.pk}"')
        self.assertContains(response, "Boissons · inactive")

    def test_reference_catalog_dry_run_and_repeat_do_not_overwrite_existing_prices(self):
        reference_activity = Activity.objects.get(slug="boutique")
        existing = Product.objects.create(
            activity=reference_activity,
            name="Macaroni Broli 250 g",
            slug="ref-macaroni-broli-250g",
            unit="paquet de 250 g",
            price=Decimal("300"),
        )

        dry_run_result = load_reference_catalog(reference_activity, dry_run=True)
        self.assertGreater(dry_run_result["categories_created"], 0)
        self.assertFalse(
            CatalogCategory.objects.filter(activity=reference_activity).exists()
        )

        first_result = load_reference_catalog(reference_activity)
        second_result = load_reference_catalog(reference_activity)
        existing.refresh_from_db()
        self.assertEqual(existing.price, Decimal("300"))
        self.assertGreater(first_result["products_created"], 0)
        self.assertEqual(second_result["categories_created"], 0)
        self.assertEqual(second_result["products_created"], 0)
        self.assertGreater(second_result["skipped"], 0)
        self.assertEqual(
            Product.objects.get(activity=reference_activity, slug="ref-macaroni-broli-250g").stock_quantity,
            0,
        )

    def test_seed_command_dry_run_reports_without_writing(self):
        call_command("seed_reference_catalog", "--activity-slug", "boutique", "--dry-run")
        activity = Activity.objects.get(slug="boutique")
        self.assertFalse(CatalogCategory.objects.filter(activity=activity).exists())
        self.assertFalse(Product.objects.filter(activity=activity, slug__startswith="ref-").exists())

    def test_seed_command_can_add_idempotent_stock_and_sales(self):
        activity = Activity.objects.get(slug="boutique")
        ActivityMembership.objects.create(
            user=self.manager, activity=activity, role=Role.MANAGER
        )

        call_command(
            "seed_reference_catalog",
            "--activity-slug",
            "boutique",
            "--include-sales",
        )

        seeded_products = Product.objects.filter(activity=activity, slug__startswith="ref-")
        self.assertGreater(seeded_products.count(), 0)
        self.assertTrue(
            all(product.stock_quantity in (19, 20) for product in seeded_products)
        )
        self.assertEqual(
            StockMovement.objects.filter(
                product__in=seeded_products,
                movement_type=StockMovement.MovementType.ENTRY,
                reason__startswith="Approvisionnement de démonstration des références PDF",
            ).count(),
            seeded_products.count(),
        )
        self.assertTrue(
            SaleLine.objects.filter(
                sale__activity=activity,
                sale__user=self.manager,
                product__slug__startswith="ref-",
            ).exists()
        )
        self.assertEqual(Sale.objects.filter(activity=activity).count(), 1)

        call_command(
            "seed_reference_catalog",
            "--activity-slug",
            "boutique",
            "--include-sales",
        )

        self.assertEqual(Sale.objects.filter(activity=activity).count(), 1)
        self.assertEqual(
            StockMovement.objects.filter(
                product__in=seeded_products,
                movement_type=StockMovement.MovementType.ENTRY,
                reason__startswith="Approvisionnement de démonstration des références PDF",
            ).count(),
            seeded_products.count(),
        )
