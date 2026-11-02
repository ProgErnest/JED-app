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

    item = forms.ChoiceField(
        label="Produit ou prestation",
        required=False,
        choices=[("", "Choisir un article ou une prestation")],
        error_messages={
            "invalid_choice": "Choisissez un produit ou une prestation de cette activité."
        },
    )

    class Meta:
        model = SaleLine
        fields = ["product", "service", "quantity"]
        widgets = {
            "product": forms.HiddenInput(),
            "service": forms.HiddenInput(),
            "quantity": forms.NumberInput(attrs={"min": "1", "value": "1", "step": "1"}),
        }

    def __init__(self, *args, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].required = False
        self.fields["service"].required = False
        self.fields["quantity"].initial = 1
        if activity is not None:
            self.fields["product"].queryset = Product.objects.filter(
                activity=activity, is_active=True, stock_quantity__gt=0
            )
            self.fields["service"].queryset = Service.objects.filter(
                activity=activity, is_active=True
            )
        products = self.fields["product"].queryset.order_by("name")
        services = self.fields["service"].queryset.order_by("name")
        self.fields["item"].choices += [
            (
                f"product:{product.pk}",
                f"{product.name} · {product.price} FCFA · stock {product.stock_quantity}",
            )
            for product in products
        ]
        self.fields["item"].choices += [
            (f"service:{service.pk}", f"{service.name} · {service.price} FCFA · prestation")
            for service in services
        ]
        self.fields["quantity"].required = False  # ligne vide autorisée

    def clean(self):
        cleaned = super().clean()
        item_value = cleaned.get("item")
        product = cleaned.get("product")
        service = cleaned.get("service")
        if item_value:
            item_type, item_pk = item_value.split(":", maxsplit=1)
            if item_type == "product":
                product = self.fields["product"].queryset.filter(pk=item_pk).first()
            elif item_type == "service":
                service = self.fields["service"].queryset.filter(pk=item_pk).first()
            cleaned["product"] = product
            cleaned["service"] = service
        quantity = cleaned.get("quantity")

        # Ligne vide (ni produit ni service) : ignorée par le formset.
        if not product and not service:
            return cleaned

        if product and service:
            self.add_error(None, "Ne choisissez qu'un produit ou un service, pas les deux.")
        if item_value and not (product or service):
            self.add_error("item", "Cet article n'est pas disponible dans cette activité.")
        if quantity is None or int(quantity) <= 0:
            self.add_error("quantity", "La quantité doit être positive.")
        elif product and quantity > product.stock_quantity:
            self.add_error(
                "quantity",
                f"Stock insuffisant : {product.stock_quantity} disponible(s).",
            )
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
    extra=1,
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
