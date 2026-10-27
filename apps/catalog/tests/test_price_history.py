from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.activities.models import Activity
from apps.catalog.models import PriceHistory, Product, Service
from apps.inventory.models import StockMovement
from apps.inventory.services import record_stock_movement


class CatalogPriceHistoryTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Shop", slug="shop")
        self.user = User.objects.create_user("catalog-user", password="t123")

    def history_for(self, item):
        return PriceHistory.objects.filter(
            content_type=ContentType.objects.get_for_model(item),
            object_id=item.pk,
        ).order_by("starts_at", "pk")

    def assert_price_history(self, item, expected):
        rows = list(self.history_for(item))
        self.assertEqual(
            [(row.price, row.ends_at is None) for row in rows],
            expected,
        )

    def test_product_price_change_creates_one_closed_version(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="soap",
            unit="piece",
            price=Decimal("10.00"),
        )
        original = self.history_for(product).get()

        product.price = Decimal("12.00")
        product._current_user = self.user
        product.save()

        self.assert_price_history(
            product,
            [(Decimal("10.00"), False), (Decimal("12.00"), True)],
        )
        original.refresh_from_db()
        self.assertIsNotNone(original.ends_at)
        current = self.history_for(product).get(ends_at__isnull=True)
        self.assertEqual(current.created_by, self.user)

    def test_non_price_product_edit_preserves_current_price_period(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="soap",
            unit="piece",
            price=Decimal("10.00"),
        )
        current = self.history_for(product).get(ends_at__isnull=True)
        original_start = current.starts_at

        product.description = "Updated description"
        product._current_user = self.user
        product.save()

        current.refresh_from_db()
        self.assertEqual(current.starts_at, original_start)
        self.assertEqual(self.history_for(product).count(), 1)

    def test_price_not_in_update_fields_does_not_change_history(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="soap",
            unit="piece",
            price=Decimal("10.00"),
        )
        current = self.history_for(product).get(ends_at__isnull=True)
        original_start = current.starts_at

        product.price = Decimal("12.00")
        product.description = "Updated description"
        product.save(update_fields=["description"])

        product.refresh_from_db()
        current.refresh_from_db()
        self.assertEqual(product.price, Decimal("10.00"))
        self.assertEqual(current.price, Decimal("10.00"))
        self.assertEqual(current.starts_at, original_start)
        self.assertEqual(self.history_for(product).count(), 1)

    def test_stock_movement_does_not_change_price_history(self):
        product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="soap",
            unit="piece",
            price=Decimal("10.00"),
        )
        original = self.history_for(product).get(ends_at__isnull=True)
        original_start = original.starts_at

        record_stock_movement(
            product=product,
            movement_type=StockMovement.MovementType.ENTRY,
            quantity=5,
            unit_cost=Decimal("4.00"),
            user=self.user,
        )

        original.refresh_from_db()
        self.assertEqual(original.starts_at, original_start)
        self.assertIsNone(original.ends_at)
        self.assertEqual(self.history_for(product).count(), 1)

    def test_service_price_change_keeps_exactly_one_row_per_price(self):
        service = Service.objects.create(
            activity=self.activity,
            name="Haircut",
            slug="haircut",
            price=Decimal("10.00"),
        )

        service.price = Decimal("15.00")
        service._current_user = self.user
        service.save()

        self.assert_price_history(
            service,
            [(Decimal("10.00"), False), (Decimal("15.00"), True)],
        )