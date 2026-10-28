from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.catalog.models import Service
from apps.sales.models import Sale
from apps.sales.services import create_sale


class SalePermissionTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Shop", slug="shop")
        self.other_activity = Activity.objects.create(name="Salon", slug="salon")
        self.global_user = User.objects.create_user("global", password="t123")
        ActivityMembership.objects.create(
            user=self.global_user, activity=None, role=Role.GLOBAL
        )
        self.manager = User.objects.create_user("manager", password="t123")
        ActivityMembership.objects.create(
            user=self.manager, activity=self.activity, role=Role.MANAGER
        )
        self.employee = User.objects.create_user("employee", password="t123")
        ActivityMembership.objects.create(
            user=self.employee, activity=self.activity, role=Role.EMPLOYEE
        )
        self.service = Service.objects.create(
            activity=self.activity,
            name="Haircut",
            slug="haircut",
            price=Decimal("20.00"),
        )

    def create_sale(self, user):
        return create_sale(
            activity=self.activity,
            user=user,
            lines_data=[{"item": self.service, "quantity": 1}],
        )

    def test_employee_sale_list_only_contains_own_sales(self):
        self.create_sale(self.global_user)
        own_sale = self.create_sale(self.employee)
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse("sales:sale_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["sales"]), [own_sale])

    def test_employee_cannot_open_colleague_sale_in_same_activity(self):
        sale = self.create_sale(self.global_user)
        self.client.force_login(self.employee)

        response = self.client.get(
            reverse(
                "sales:sale_detail",
                kwargs={"activity_slug": self.activity.slug, "pk": sale.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_manager_can_see_employee_sales(self):
        sale = self.create_sale(self.employee)
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("sales:sale_list", kwargs={"activity_slug": self.activity.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["sales"]), [sale])

    def test_superuser_can_access_other_activity(self):
        superuser = User.objects.create_superuser(
            "root", email="root@example.test", password="t123"
        )
        self.client.force_login(superuser)

        response = self.client.get(
            reverse(
                "sales:sale_list",
                kwargs={"activity_slug": self.other_activity.slug},
            )
        )

        self.assertEqual(response.status_code, 200)
