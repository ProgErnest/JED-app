from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity


class ActivityMembershipConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="membership-user")
        cls.activity = Activity.objects.create(
            name="Test activity",
            slug="test-activity",
        )

    def assert_database_rejects(self, **membership_fields):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ActivityMembership.objects.create(
                    user=self.user,
                    **membership_fields,
                )

    def test_global_role_cannot_be_linked_to_an_activity(self):
        self.assert_database_rejects(
            activity=self.activity,
            role=Role.GLOBAL,
        )

    def test_activity_role_requires_an_activity(self):
        for role in (Role.MANAGER, Role.EMPLOYEE):
            with self.subTest(role=role):
                self.assert_database_rejects(activity=None, role=role)

    def test_user_can_have_only_one_global_membership(self):
        ActivityMembership.objects.create(
            user=self.user,
            activity=None,
            role=Role.GLOBAL,
        )
        self.assert_database_rejects(activity=None, role=Role.GLOBAL)

    def test_user_can_have_distinct_activity_memberships(self):
        second_activity = Activity.objects.create(
            name="Second activity",
            slug="second-activity",
        )
        ActivityMembership.objects.create(
            user=self.user,
            activity=self.activity,
            role=Role.MANAGER,
        )
        membership = ActivityMembership.objects.create(
            user=self.user,
            activity=second_activity,
            role=Role.EMPLOYEE,
        )

        self.assertEqual(membership.activity, second_activity)
