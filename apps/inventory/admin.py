"""Administration de l'application ``inventory`` (JED-05)."""

from django.contrib import admin

from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("movement_type", "product", "quantity", "unit_cost", "activity", "user", "created_at")
    list_filter = ("movement_type", "activity", "created_at")
    search_fields = ("product__name", "reason", "user__username")
    raw_id_fields = ("product", "user", "activity")
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
