from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.activities.models import Activity
from apps.accounts.models import ActivityMembership, Role
from apps.expenses.models import Expense, ExpenseCategory


class ExpenseModelTest(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Boutique JED-09", slug="boutique-jed09")
        self.user = User.objects.create_user("depensier", password="t123")
        ActivityMembership.objects.create(
            user=self.user,
            activity=self.activity,
            role=Role.EMPLOYEE,
            is_active=True,
        )
        self.category = ExpenseCategory.objects.create(
            activity=self.activity,
            name="Loyer",
            slug="loyer-jed09",
        )

    def test_expense_requires_positive_amount(self):
        with self.assertRaises(ValidationError):
            Expense(
                activity=self.activity,
                category=self.category,
                user=self.user,
                amount=Decimal("0"),
                description="vide",
            ).full_clean()

    def test_expense_category_must_match_activity(self):
        other_activity = Activity.objects.create(name="Coiffure JED-09", slug="coiffure-jed09")
        other_category = ExpenseCategory.objects.create(
            activity=other_activity,
            name="Marketing",
            slug="marketing-jed09",
        )
        expense = Expense(
            activity=self.activity,
            category=other_category,
            user=self.user,
            amount=Decimal("12.50"),
            description="Erreur de catégorie",
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_cancel_marks_expense_and_keeps_audit(self):
        expense = Expense.objects.create(
            activity=self.activity,
            category=self.category,
            user=self.user,
            amount=Decimal("42.00"),
            description="Facture électricité",
        )

        expense.cancel(user=self.user, reason="Facture annulée")

        self.assertTrue(expense.is_canceled)
        self.assertEqual(expense.cancellation_reason, "Facture annulée")
        self.assertEqual(expense.audit_logs.count(), 2)
