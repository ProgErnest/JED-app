"""Formulaires du catalogue (JED-04)."""

from django import forms
from django.db.models import Q
from django.utils.text import slugify

from .models import CatalogCategory, Product, Service


class CatalogCategoryForm(forms.ModelForm):
    class Meta:
        model = CatalogCategory
        fields = ["name", "sort_order", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields.pop("is_active")

    def save(self, commit=True):
        if not self.instance.pk:
            base_slug = slugify(self.cleaned_data["name"]) or "rubrique"
            slug = base_slug
            suffix = 2
            categories = CatalogCategory.objects.filter(activity=self.instance.activity)
            while categories.filter(slug=slug).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.instance.slug = slug
        return super().save(commit=commit)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "unit", "description", "price", "category", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        category_activity = activity or self.instance.activity
        categories = CatalogCategory.objects.none()
        if category_activity is not None:
            categories = CatalogCategory.objects.filter(activity=category_activity)
            if self.instance.category_id:
                categories = categories.filter(
                    Q(is_active=True) | Q(pk=self.instance.category_id)
                )
            else:
                categories = categories.filter(is_active=True)
        self.fields["category"].queryset = categories.order_by("sort_order", "name")
        self.fields["category"].required = False
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
        fields = ["name", "slug", "description", "price", "duration_minutes", "category", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "duration_minutes": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, activity=None, **kwargs):
        super().__init__(*args, **kwargs)
        category_activity = activity or self.instance.activity
        categories = CatalogCategory.objects.none()
        if category_activity is not None:
            categories = CatalogCategory.objects.filter(activity=category_activity)
            if self.instance.category_id:
                categories = categories.filter(
                    Q(is_active=True) | Q(pk=self.instance.category_id)
                )
            else:
                categories = categories.filter(is_active=True)
        self.fields["category"].queryset = categories.order_by("sort_order", "name")
        self.fields["category"].required = False
        self.fields["price"].label = "Prix de la prestation (FCFA)"
        self.fields.pop("slug")
        if not self.instance.pk:
            self.fields.pop("is_active")

    def save(self, commit=True):
        if not self.instance.pk:
            base_slug = slugify(self.cleaned_data["name"]) or "prestation"
            slug = base_slug
            suffix = 2
            existing_services = Service.objects.filter(activity=self.instance.activity)
            while existing_services.filter(slug=slug).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.instance.slug = slug
        return super().save(commit=commit)
