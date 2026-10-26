"""Formulaires du catalogue (JED-04)."""

from django import forms

from .models import Product, Service


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "slug", "unit", "description", "price", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "slug", "description", "price", "duration_minutes", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "duration_minutes": forms.NumberInput(attrs={"min": "0"}),
        }
