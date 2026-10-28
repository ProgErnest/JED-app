from django.test import TestCase
from django.urls import reverse

from django.contrib.auth.models import User
from decimal import Decimal

from apps.accounts.models import ActivityMembership, Role
from apps.activities.models import Activity
from apps.expenses.models import Expense, ExpenseAuditLog, ExpenseCategory


class ExpenseViewAccessTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(
            name="Boutique views JED-09 unique",
            slug="boutique-expense-views-unique",
            description="Test activity",
        )
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="secret123",
        )
        ActivityMembership.objects.create(
            user=self.user,
            activity=self.activity,
            role=Role.EMPLOYEE,
        )
        self.category = ExpenseCategory.objects.create(
            activity=self.activity,
            name="Loyer",
            slug="loyer-expense-views",
        )
        self.client.force_login(self.user)

    def test_expense_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("expenses:expense-list"))
        self.assertEqual(response.status_code, 302)

    def test_expense_list_renders(self):
        response = self.client.get(reverse("expenses:expense-list"), {"activity": self.activity.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dépenses")

    def test_expense_correction_requires_reason_and_audits_changes(self):
        expense = Expense.objects.create(
            activity=self.activity,
            category=self.category,
            user=self.user,
            amount=Decimal("10.00"),
            description="Description initiale",
        )
        url = reverse("expenses:expense-edit", args=[expense.pk])
        response = self.client.post(
            f"{url}?activity={self.activity.slug}",
            {
                "category": self.category.pk,
                "amount": "12.50",
                "description": "Description corrigée",
                "reason": "Montant de facture rectifié",
            },
        )
        self.assertEqual(response.status_code, 302)
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal("12.50"))
        self.assertEqual(expense.user, self.user)
        correction = expense.audit_logs.get(action=ExpenseAuditLog.Action.UPDATED)
        self.assertIn("Montant de facture rectifié", correction.reason)
        self.assertIn("10.00 -> 12.50", correction.reason)

    def test_employee_cannot_see_another_employees_expense(self):
        other_user = User.objects.create_user(username="other", password="secret123")
        expense = Expense.objects.create(
            activity=self.activity,
            category=self.category,
            user=other_user,
            amount=Decimal("18.00"),
        )
        response = self.client.get(
            reverse("expenses:expense-detail", args=[expense.pk]),
            {"activity": self.activity.slug},
        )
        self.assertEqual(response.status_code, 404)
