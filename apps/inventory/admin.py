"""Administration de l'application ``inventory`` (JED-05)."""

from django.contrib import admin

from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "movement_type",
        "product",
        "quantity",
        "counted_quantity",
        "unit_cost",
        "activity",
        "user",
        "created_at",
    )
    list_filter = ("movement_type", "activity", "created_at")
    search_fields = ("product__name", "reason", "user__username")
    raw_id_fields = ("product", "user", "activity")
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("inventory.view_stockmovement")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
