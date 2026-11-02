"""Formulaires des mouvements de stock (JED-05)."""

from django import forms

from .models import StockMovement


class StockEntryForm(forms.ModelForm):
    """Saisie d'une entrée de stock (approvisionnement)."""

    class Meta:
        model = StockMovement
        fields = ["product", "quantity", "unit_cost", "reason", "movement_type"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "unit_cost": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "reason": forms.TextInput(),
            "movement_type": forms.HiddenInput(),
        }

    def __init__(self, *args, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unit_cost"].label = "Coût unitaire d'achat (FCFA)"
        if activity is not None:
            self.fields["product"].queryset = self.fields["product"].queryset.filter(
                activity=activity
            )
        # Le type de mouvement est imposé par la vue (entrée), pas saisi par l'utilisateur.
        self.fields["movement_type"].required = False
        self.fields["movement_type"].widget = forms.HiddenInput()

    def clean(self):
        cleaned = super().clean()
        cleaned["movement_type"] = StockMovement.MovementType.ENTRY
        return cleaned


class StockCorrectionForm(forms.ModelForm):
    """Saisie d'une correction/perte de stock (JED-06).

    Le motif est obligatoire. La quantité est signée : positive pour un
    ajout, négative pour une perte.
    """

    class Meta:
        model = StockMovement
        fields = ["product", "quantity", "reason", "movement_type"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "1"}),
            "reason": forms.TextInput(),
            "movement_type": forms.HiddenInput(),
        }

    def __init__(self, *args, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        if activity is not None:
            self.fields["product"].queryset = self.fields["product"].queryset.filter(
                activity=activity
            )
        self.fields["movement_type"].required = False
        self.fields["reason"].required = True

    def clean(self):
        cleaned = super().clean()
        cleaned["movement_type"] = StockMovement.MovementType.CORRECTION
        return cleaned
