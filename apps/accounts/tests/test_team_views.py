from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity


class TeamManagementViewTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Boutique équipe", slug="boutique-equipe")
        self.other_activity = Activity.objects.create(name="Salon équipe", slug="salon-equipe")
        self.manager = User.objects.create_user("manager", password="test-password")
        ActivityMembership.objects.create(
            user=self.manager,
            activity=self.activity,
            role=Role.MANAGER,
        )
        self.employee = User.objects.create_user("employee", password="test-password")
        self.employee_membership = ActivityMembership.objects.create(
            user=self.employee,
            activity=self.activity,
            role=Role.EMPLOYEE,
        )
        self.other_employee = User.objects.create_user("other-employee", password="test-password")
        self.other_membership = ActivityMembership.objects.create(
            user=self.other_employee,
            activity=self.other_activity,
            role=Role.EMPLOYEE,
        )
        self.global_user = User.objects.create_user("global", password="test-password")
        ActivityMembership.objects.create(user=self.global_user, role=Role.GLOBAL)

    def test_manager_sees_only_accounts_in_managed_activity(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("accounts:team_activity", args=[self.activity.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.username)
        self.assertNotContains(response, self.other_employee.username)

    def test_team_list_hides_inactive_memberships_and_users(self):
        inactive_access_user = User.objects.create_user(
            "inactive-access", password="test-password"
        )
        ActivityMembership.objects.create(
            user=inactive_access_user,
            activity=self.activity,
            role=Role.EMPLOYEE,
            is_active=False,
        )
        inactive_account = User.objects.create_user(
            "inactive-account", password="test-password", is_active=False
        )
        ActivityMembership.objects.create(
            user=inactive_account,
            activity=self.activity,
            role=Role.EMPLOYEE,
        )

        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("accounts:team_activity", args=[self.activity.slug])
        )

        self.assertContains(response, self.employee.username)
        self.assertNotContains(response, "inactive-access")
        self.assertNotContains(response, "inactive-account")

    def test_global_list_uses_one_account_deactivation_action(self):
        self.client.force_login(self.global_user)
        response = self.client.get(reverse("accounts:team_global"))

        self.assertContains(response, self.employee.username)
        self.assertContains(response, reverse("accounts:account_deactivate", args=[self.employee.pk]))
        self.assertNotContains(response, reverse("accounts:team_deactivate", args=[self.employee_membership.pk]))

    def test_global_create_form_shows_only_account_and_access_fields(self):
        self.client.force_login(self.global_user)
        response = self.client.get(reverse("accounts:team_create_global"))

        self.assertEqual(response.status_code, 200)
        for field_name in ("username", "first_name", "last_name", "password", "activity", "role"):
            self.assertContains(response, f'name="{field_name}"')
        for field_name in ("email", "is_active", "user_is_active"):
            self.assertNotContains(response, f'name="{field_name}"')

    def test_employee_home_opens_sale_form_directly(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("accounts:home"))
        self.assertRedirects(
            response,
            reverse("sales:sale_add", args=[self.activity.slug]),
        )

    def test_root_redirects_anonymous_user_to_login(self):
        response = self.client.get("/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("accounts:login"))

    def test_root_redirects_employee_to_accounts_home(self):
        self.client.force_login(self.employee)
        response = self.client.get("/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.request["PATH_INFO"],
            reverse("sales:sale_add", args=[self.activity.slug]),
        )

    def test_root_redirects_manager_to_activity_dashboard(self):
        self.client.force_login(self.manager)
        response = self.client.get("/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.request["PATH_INFO"],
            reverse("analytics:activity-dashboard", args=[self.activity.slug]),
        )

    def test_root_redirects_global_user_to_global_dashboard(self):
        self.client.force_login(self.global_user)
        response = self.client.get("/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.request["PATH_INFO"],
            reverse("analytics:global-dashboard"),
        )

    def test_manager_can_create_employee_in_managed_activity(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("accounts:team_create_activity", args=[self.activity.slug]),
            {
                "username": "new-employee",
                "first_name": "Awa",
                "last_name": "Test",
                "email": "awa@example.test",
                "role": Role.EMPLOYEE,
                "is_active": "on",
                "password": "Long-Test-Password-2026!",
            },
        )
        self.assertEqual(response.status_code, 302)
        membership = ActivityMembership.objects.get(user__username="new-employee")
        self.assertEqual(membership.activity, self.activity)
        self.assertEqual(membership.role, Role.EMPLOYEE)
        self.assertTrue(membership.is_active)

    def test_manager_cannot_assign_global_role(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("accounts:team_create_activity", args=[self.activity.slug]),
            {
                "username": "attempt-global",
                "role": Role.GLOBAL,
                "is_active": "on",
                "password": "Long-Test-Password-2026!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="attempt-global").exists())

    def test_manager_cannot_open_another_activity_team(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("accounts:team_activity", args=[self.other_activity.slug])
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_edit_or_deactivate_membership_in_other_activity(self):
        self.client.force_login(self.manager)
        edit_response = self.client.get(
            reverse("accounts:team_edit", args=[self.other_membership.pk])
        )
        deactivate_response = self.client.post(
            reverse("accounts:team_deactivate", args=[self.other_membership.pk])
        )
        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(deactivate_response.status_code, 403)
        self.other_membership.refresh_from_db()
        self.assertTrue(self.other_membership.is_active)

    def test_manager_can_deactivate_member_access_by_post_only(self):
        self.client.force_login(self.manager)
        url = reverse("accounts:team_deactivate", args=[self.employee_membership.pk])
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 403)
        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, 302)
        self.employee_membership.refresh_from_db()
        self.assertFalse(self.employee_membership.is_active)
        self.assertTrue(self.employee.is_active)

    def test_manager_can_change_member_role_in_managed_activity(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("accounts:team_edit", args=[self.employee_membership.pk]),
            {
                "username": self.employee.username,
                "first_name": "",
                "last_name": "",
                "email": "",
                "role": Role.MANAGER,
                "is_active": "on",
                "password": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.employee_membership.refresh_from_db()
        self.assertEqual(self.employee_membership.role, Role.MANAGER)

    def test_manager_cannot_modify_or_disable_own_access(self):
        manager_membership = self.manager.activity_memberships.get()
        self.client.force_login(self.manager)
        edit_response = self.client.post(
            reverse("accounts:team_edit", args=[manager_membership.pk]),
            {},
        )
        deactivate_response = self.client.post(
            reverse("accounts:team_deactivate", args=[manager_membership.pk])
        )
        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(deactivate_response.status_code, 403)
        manager_membership.refresh_from_db()
        self.assertTrue(manager_membership.is_active)

    def test_global_can_assign_global_role(self):
        self.client.force_login(self.global_user)
        response = self.client.post(
            reverse("accounts:team_create_global"),
            {
                "username": "new-global",
                "role": Role.GLOBAL,
                "is_active": "on",
                "user_is_active": "on",
                "password": "Long-Test-Password-2026!",
            },
        )
        self.assertEqual(response.status_code, 302)
        membership = ActivityMembership.objects.get(user__username="new-global")
        self.assertEqual(membership.role, Role.GLOBAL)
        self.assertIsNone(membership.activity)

    def test_global_can_add_access_to_existing_user_without_changing_password(self):
        existing = User.objects.create_user(
            "existing-user",
            password="Original-Password-2026!",
            first_name="Nom existant",
        )
        self.client.force_login(self.global_user)
        response = self.client.post(
            reverse("accounts:team_create_global"),
            {
                "username": "existing-user",
                "first_name": "Valeur ignorée",
                "last_name": "",
                "email": "",
                "role": Role.EMPLOYEE,
                "activity": self.activity.pk,
                "is_active": "on",
                "user_is_active": "on",
                "password": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        membership = ActivityMembership.objects.get(
            user=existing,
            activity=self.activity,
        )
        self.assertEqual(membership.role, Role.EMPLOYEE)
        existing.refresh_from_db()
        self.assertEqual(existing.first_name, "Nom existant")
        self.assertTrue(existing.check_password("Original-Password-2026!"))

    def test_only_global_can_disable_whole_account(self):
        self.client.force_login(self.manager)
        denied = self.client.post(
            reverse("accounts:account_deactivate", args=[self.employee.pk])
        )
        self.assertEqual(denied.status_code, 403)
        self.client.force_login(self.global_user)
        accepted = self.client.post(
            reverse("accounts:account_deactivate", args=[self.employee.pk])
        )
        self.assertEqual(accepted.status_code, 302)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
