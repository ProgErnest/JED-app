"""Administration de l'application ``catalog`` (JED-04)."""

from django.contrib import admin

from .models import PriceHistory, Product, Service


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "activity", "unit", "price", "is_active", "updated_at")
    list_filter = ("activity", "is_active", "unit")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("activity__name", "name")
    raw_id_fields = ("activity",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "activity", "price", "duration_minutes", "is_active", "updated_at")
    list_filter = ("activity", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("activity__name", "name")
    raw_id_fields = ("activity",)


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("item", "price", "starts_at", "created_by")
    list_filter = ("starts_at",)
    raw_id_fields = ("created_by",)
    ordering = ("-starts_at",)
