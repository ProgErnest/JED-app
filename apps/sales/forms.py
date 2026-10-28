"""Formulaires des ventes (JED-07).

Permettent la saisie d'un ticket de caisse avec plusieurs lignes pouvant
mélanger produits et prestations (décision A7).
"""

from __future__ import annotations

from django import forms

from apps.catalog.models import Product, Service

from .models import Sale, SaleLine


class SaleLineForm(forms.ModelForm):
    """Une ligne de ticket : produit OU service, avec quantité."""

    class Meta:
        model = SaleLine
        fields = ["product", "service", "quantity"]
        widgets = {
            "product": forms.Select(attrs={"class": "line-item-select"}),
            "service": forms.Select(attrs={"class": "line-item-select"}),
            "quantity": forms.NumberInput(attrs={"min": "1", "value": "1", "step": "1"}),
        }

    def __init__(self, *args, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].required = False
        self.fields["service"].required = False
        self.fields["quantity"].initial = 1
        if activity is not None:
            self.fields["product"].queryset = Product.objects.filter(
                activity=activity, is_active=True
            )
            self.fields["service"].queryset = Service.objects.filter(
                activity=activity, is_active=True
            )
        self.fields["quantity"].required = False  # ligne vide autorisée

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        service = cleaned.get("service")
        quantity = cleaned.get("quantity")

        # Ligne vide (ni produit ni service) : ignorée par le formset.
        if not product and not service:
            return cleaned

        if product and service:
            self.add_error(None, "Ne choisissez qu'un produit ou un service, pas les deux.")
        if quantity is None or int(quantity) <= 0:
            self.add_error("quantity", "La quantité doit être positive.")
        return cleaned


class BaseSaleLineFormSet(forms.BaseInlineFormSet):
    """Formset des lignes de ticket : au moins une ligne non vide."""

    def clean(self):
        super().clean()
        has_line = False
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data:
                continue
            product = form.cleaned_data.get("product")
            service = form.cleaned_data.get("service")
            quantity = form.cleaned_data.get("quantity")
            if product or service:
                if quantity is None or quantity <= 0:
                    form.add_error("quantity", "La quantité doit être positive.")
                else:
                    has_line = True
        if not has_line:
            raise forms.ValidationError(
                "Le ticket doit contenir au moins un produit ou un service."
            )


SaleLineFormSet = forms.inlineformset_factory(
    Sale,
    SaleLine,
    form=SaleLineForm,
    formset=BaseSaleLineFormSet,
    extra=3,
    can_delete=False,
    fields=["product", "service", "quantity"],
)


class SaleCancellationForm(forms.Form):
    reason = forms.CharField(
        label="Motif de l'annulation",
        widget=forms.Textarea(attrs={"rows": 3}),
        strip=True,
    )

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if not reason:
            raise forms.ValidationError("Le motif d'annulation est obligatoire.")
        return reason
