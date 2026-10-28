from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from apps.activities.models import Activity
from apps.catalog.models import Product
from apps.inventory.models import StockMovement
from apps.inventory.services import record_stock_movement


class RecordStockMovementTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Shop", slug="shop")
        self.other_activity = Activity.objects.create(
            name="Salon", slug="salon"
        )
        self.user = User.objects.create_user("stock-user", password="t123")
        self.product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="soap",
            unit="piece",
            price=Decimal("10.00"),
            stock_quantity=10,
            average_cost=Decimal("2.00"),
        )

    def record_entry(self, quantity, unit_cost):
        return record_stock_movement(
            product=self.product,
            movement_type=StockMovement.MovementType.ENTRY,
            quantity=quantity,
            unit_cost=unit_cost,
            user=self.user,
        )

    def test_successive_entries_update_weighted_average_and_movement(self):
        self.record_entry(10, Decimal("4.00"))

        self.product.refresh_from_db()
        movement = StockMovement.objects.get()

        self.assertEqual(self.product.stock_quantity, 20)
        self.assertEqual(self.product.average_cost, Decimal("3.00"))
        self.assertEqual(movement.product, self.product)
        self.assertEqual(movement.activity, self.activity)
        self.assertEqual(movement.quantity, 10)
        self.assertEqual(movement.unit_cost, Decimal("4.00"))
        self.assertEqual(movement.user, self.user)

    def test_entry_when_stock_is_zero_uses_entry_cost(self):
        self.product.stock_quantity = 0
        self.product.save(update_fields=["stock_quantity"])

        self.record_entry(4, Decimal("6.25"))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 4)
        self.assertEqual(self.product.average_cost, Decimal("6.25"))

    def test_negative_stock_keeps_unreliable_cost_until_positive(self):
        self.product.stock_quantity = -5
        self.product.save(update_fields=["stock_quantity"])

        self.record_entry(5, Decimal("7.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)
        self.assertEqual(self.product.average_cost, Decimal("2.00"))

        self.record_entry(6, Decimal("7.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 6)
        self.assertEqual(self.product.average_cost, Decimal("7.00"))

    def test_rejects_activity_that_does_not_match_product(self):
        self.assert_rejected_without_changes(
            lambda: record_stock_movement(
                product=self.product,
                movement_type=StockMovement.MovementType.ENTRY,
                quantity=1,
                unit_cost=Decimal("3.00"),
                user=self.user,
                activity=self.other_activity,
            )
        )

    def test_rejects_invalid_entry_quantity_and_cost(self):
        invalid_entries = (
            {"quantity": 0, "unit_cost": Decimal("3.00")},
            {"quantity": -1, "unit_cost": Decimal("3.00")},
            {"quantity": 1, "unit_cost": None},
            {"quantity": 1, "unit_cost": Decimal("-0.01")},
            {"quantity": 1, "unit_cost": Decimal("NaN")},
        )
        for values in invalid_entries:
            with self.subTest(values=values):
                self.assert_rejected_without_changes(
                    lambda: self.record_entry(**values)
                )

    def test_rejects_unknown_movement_type_and_zero_correction(self):
        invalid_movements = (
            ("OTHER", 1),
            (StockMovement.MovementType.EXIT, 0),
            (StockMovement.MovementType.CORRECTION, 0),
        )
        for movement_type, quantity in invalid_movements:
            with self.subTest(movement_type=movement_type, quantity=quantity):
                self.assert_rejected_without_changes(
                    lambda: record_stock_movement(
                        product=self.product,
                        movement_type=movement_type,
                        quantity=quantity,
                        user=self.user,
                    )
                )

    def test_rejects_correction_without_nonblank_reason(self):
        for reason in ("", "   ", None):
            with self.subTest(reason=reason):
                self.assert_rejected_without_changes(
                    lambda: record_stock_movement(
                        product=self.product,
                        movement_type=StockMovement.MovementType.CORRECTION,
                        quantity=-1,
                        user=self.user,
                        reason=reason,
                    )
                )

    def test_failure_to_create_movement_rolls_back_product_update(self):
        with patch(
            "apps.inventory.services.StockMovement.objects.create",
            side_effect=RuntimeError("movement insert failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "movement insert failed"):
                self.record_entry(5, Decimal("4.00"))

        self.assert_product_unchanged()
        self.assertEqual(StockMovement.objects.count(), 0)

    def assert_product_unchanged(self):
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(self.product.average_cost, Decimal("2.00"))
        self.assertEqual(StockMovement.objects.count(), 0)

    def assert_rejected_without_changes(self, operation):
        try:
            with transaction.atomic():
                operation()
                transaction.set_rollback(True)
        except ValidationError:
            pass
        else:
            self.fail("Expected the stock operation to be rejected.")
        self.assert_product_unchanged()