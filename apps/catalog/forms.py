"""Formulaires du catalogue (JED-04)."""

from django import forms
from django.utils.text import slugify

from .models import Product, Service


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "unit", "description", "price", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price"].label = "Prix de vente (FCFA)"
        if self.instance.pk:
            self.fields["is_active"].label = "Disponible à la vente"
        else:
            self.fields.pop("is_active")

    def save(self, commit=True):
        if not self.instance.pk:
            base_slug = slugify(self.cleaned_data["name"]) or "produit"
            slug = base_slug
            suffix = 2
            existing_products = Product.objects.filter(activity=self.instance.activity)
            while existing_products.filter(slug=slug).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.instance.slug = slug
        return super().save(commit=commit)


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "slug", "description", "price", "duration_minutes", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "duration_minutes": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price"].label = "Prix de la prestation (FCFA)"
