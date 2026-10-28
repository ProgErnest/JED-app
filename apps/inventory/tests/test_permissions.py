from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.catalog.admin import ProductAdmin
from apps.catalog.models import Product
from apps.inventory.models import StockMovement
from apps.inventory.admin import StockMovementAdmin
from apps.inventory.services import record_stock_movement


class StockMovementPermissionTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Shop", slug="shop")
        self.global_user = User.objects.create_user("global", password="t123")
        ActivityMembership.objects.create(
            user=self.global_user, role=Role.GLOBAL, activity=None
        )
        self.manager = User.objects.create_user("manager", password="t123")
        ActivityMembership.objects.create(
            user=self.manager, role=Role.MANAGER, activity=self.activity
        )
        self.employee = User.objects.create_user("employee", password="t123")
        ActivityMembership.objects.create(
            user=self.employee, role=Role.EMPLOYEE, activity=self.activity
        )
        self.product = Product.objects.create(
            activity=self.activity,
            name="Soap",
            slug="soap",
            unit="piece",
            price="10.00",
        )
        for user in (self.global_user, self.employee):
            record_stock_movement(
                product=self.product,
                movement_type=StockMovement.MovementType.CORRECTION,
                quantity=1,
                user=user,
                reason="Inventory count",
            )

    def test_employee_only_sees_own_stock_movements(self):
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse("inventory:movement_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["movements"]),
            list(StockMovement.objects.filter(user=self.employee)),
        )

    def test_manager_sees_all_stock_movements_in_activity(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("inventory:movement_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["movements"].count(), 2)

    def test_employee_can_submit_correction_and_reason_is_recorded(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse(
                "inventory:movement_correction_add",
                kwargs={"activity_slug": self.activity.slug},
            ),
            {"product": self.product.pk, "quantity": "-2", "reason": "Perte"},
        )

        self.assertRedirects(
            response,
            reverse("inventory:movement_list", kwargs={"activity_slug": self.activity.slug}),
        )
        self.product.refresh_from_db()
        movement = StockMovement.objects.get(user=self.employee, reason="Perte")
        self.assertEqual(self.product.stock_quantity, 0)
        self.assertEqual(movement.quantity, -2)
        self.assertEqual(movement.reason, "Perte")

    def test_correction_form_rejects_blank_reason(self):
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse(
                "inventory:movement_correction_add",
                kwargs={"activity_slug": self.activity.slug},
            ),
            {"product": self.product.pk, "quantity": "-2", "reason": "   "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StockMovement.objects.count(), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)

    def test_movement_list_exposes_correction_action(self):
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse("inventory:movement_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertContains(response, reverse(
            "inventory:movement_correction_add",
            kwargs={"activity_slug": self.activity.slug},
        ))

    def test_product_deletion_cannot_erase_movement_history(self):
        with self.assertRaises(ProtectedError):
            self.product.delete()

        self.assertEqual(StockMovement.objects.filter(product=self.product).count(), 2)

    def test_stock_movements_are_not_mutable_in_admin(self):
        movement_admin = StockMovementAdmin(StockMovement, AdminSite())
        staff_user = User.objects.create_superuser("stock-admin", password="t123")
        request = RequestFactory().get("/admin/")
        request.user = staff_user

        self.assertTrue(movement_admin.has_view_permission(request))
        self.assertFalse(movement_admin.has_add_permission(None))
        self.assertFalse(movement_admin.has_change_permission(None))
        self.assertFalse(movement_admin.has_delete_permission(None))

    def test_product_stock_fields_are_read_only_in_admin(self):
        product_admin = ProductAdmin(Product, AdminSite())

        self.assertIn("stock_quantity", product_admin.get_readonly_fields(None))
        self.assertIn("average_cost", product_admin.get_readonly_fields(None))