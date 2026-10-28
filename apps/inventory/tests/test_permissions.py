from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.catalog.models import Product
from apps.inventory.models import StockMovement
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