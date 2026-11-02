from __future__ import annotations

from django import forms

from .models import Expense, ExpenseCategory


class ExpenseForm(forms.ModelForm):
    """Formulaire de création d'une dépense pour une activité."""

    class Meta:
        model = Expense
        fields = ["category", "amount", "description"]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount"].label = "Montant (FCFA)"
        self.activity = activity
        if activity is not None:
            self.fields["category"].queryset = ExpenseCategory.objects.filter(
                activity=activity,
            )

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Le montant doit être strictement positif.")
        return amount

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if category and self.activity and category.activity_id != self.activity.pk:
            raise forms.ValidationError(
                "La catégorie doit appartenir à l'activité de la dépense."
            )
        return cleaned


class ExpenseCancelForm(forms.Form):
    reason = forms.CharField(
        label="Motif d'annulation",
        widget=forms.Textarea(attrs={"rows": 3}),
        strip=True,
    )

    def clean_reason(self):
        reason = (self.cleaned_data.get("reason") or "").strip()
        if not reason:
            raise forms.ValidationError("Le motif d'annulation est obligatoire.")
        return reason


class ExpenseCorrectionForm(ExpenseForm):
    reason = forms.CharField(
        label="Motif de correction",
        widget=forms.Textarea(attrs={"rows": 3}),
        strip=True,
    )

    def clean_reason(self):
        reason = (self.cleaned_data.get("reason") or "").strip()
        if not reason:
            raise forms.ValidationError("Le motif de correction est obligatoire.")
        return reason
