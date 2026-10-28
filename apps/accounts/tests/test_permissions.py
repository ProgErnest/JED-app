from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import ActivityMembership, Role
from apps.accounts.permissions import (
    get_accessible_activities,
    user_can_manage_team,
    user_has_activity_access,
    user_is_employee_in_activity,
    user_is_global,
)
from apps.activities.models import Activity


class SuperuserPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.activity = Activity.objects.create(name="Shop", slug="shop")
        cls.superuser = User.objects.create_superuser(
            username="root", email="root@example.test", password="t123"
        )

    def test_superuser_is_global_for_permission_helpers(self):
        self.assertTrue(user_is_global(self.superuser))
        self.assertTrue(user_has_activity_access(self.superuser, self.activity))
        self.assertTrue(user_can_manage_team(self.superuser, self.activity))

    def test_superuser_can_list_all_activities(self):
        self.assertQuerySetEqual(
            get_accessible_activities(self.superuser),
            Activity.objects.all(),
            ordered=False,
        )

    def test_superuser_can_manage_team_without_membership(self):
        self.assertTrue(user_can_manage_team(self.superuser, self.activity))

    def test_global_membership_is_not_restricted_as_employee(self):
        ActivityMembership.objects.create(
            user=self.superuser,
            activity=self.activity,
            role=Role.EMPLOYEE,
        )

        self.assertFalse(user_is_employee_in_activity(self.superuser, self.activity))