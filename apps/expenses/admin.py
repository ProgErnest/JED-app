from django.contrib import admin

from .models import Expense, ExpenseAuditLog, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "activity", "slug", "created_at")
    list_filter = ("activity",)
    search_fields = ("name", "slug", "activity__name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "amount", "activity", "user", "is_canceled", "created_at")
    list_filter = ("activity", "category", "is_canceled", "created_at")
    search_fields = ("description", "user__username", "category__name")
    readonly_fields = ("created_at", "updated_at", "canceled_by", "canceled_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExpenseAuditLog)
class ExpenseAuditLogAdmin(admin.ModelAdmin):
    list_display = ("expense", "action", "user", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("expense__description", "user__username", "reason")
    readonly_fields = ("expense", "user", "action", "reason", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False