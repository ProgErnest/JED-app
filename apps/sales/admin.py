"""Administration de l'application ``sales`` (JED-07)."""

from django.contrib import admin

from apps.accounts.permissions import user_is_global

from .models import Sale, SaleCancellation, SaleLine


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 0
    can_delete = False
    show_change_link = False
    autocomplete_fields = ["product", "service"]
    fields = ("product", "service", "quantity", "unit_price", "cost", "margin_reliable", "total")
    readonly_fields = ("product", "service", "quantity", "unit_price", "cost", "margin_reliable", "total")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "activity", "user", "created_at", "total")
    list_filter = ("activity", "created_at", "user")
    search_fields = ("user__username",)
    readonly_fields = ("activity", "user", "created_at", "updated_at", "total")
    inlines = [SaleLineInline]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return user_is_global(request.user) and request.user.has_perm("sales.view_sale")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaleLine)
class SaleLineAdmin(admin.ModelAdmin):
    list_display = ("sale", "item_display", "quantity", "unit_price", "cost", "margin_reliable", "total")
    list_filter = ("sale__activity", "sale__created_at")
    readonly_fields = ("sale", "product", "service", "quantity", "unit_price", "cost", "margin_reliable", "total")

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return user_is_global(request.user) and request.user.has_perm("sales.view_saleline")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaleCancellation)
class SaleCancellationAdmin(admin.ModelAdmin):
    list_display = ("sale", "user", "created_at", "reason")
    list_filter = ("sale__activity", "created_at")
    search_fields = ("sale__id", "reason", "user__username")
    readonly_fields = ("sale", "user", "reason", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return user_is_global(request.user) and request.user.has_perm("sales.view_salecancellation")

    def has_delete_permission(self, request, obj=None):
        return False
