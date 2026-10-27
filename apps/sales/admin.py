"""Administration de l'application ``sales`` (JED-07)."""

from django.contrib import admin

from .models import Sale, SaleLine


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 0
    autocomplete_fields = ["product", "service"]
    fields = ("product", "service", "quantity", "unit_price", "cost", "total")
    readonly_fields = ("unit_price", "cost", "total")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "activity", "user", "created_at", "total")
    list_filter = ("activity", "created_at", "user")
    search_fields = ("user__username",)
    readonly_fields = ("total",)
    inlines = [SaleLineInline]
    date_hierarchy = "created_at"


@admin.register(SaleLine)
class SaleLineAdmin(admin.ModelAdmin):
    list_display = ("sale", "item_display", "quantity", "unit_price", "cost", "total")
    list_filter = ("sale__activity", "sale__created_at")
