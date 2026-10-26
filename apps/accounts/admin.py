"""Administration de l'application ``accounts`` (JED-02)."""

from django.contrib import admin
from django.contrib.auth.models import User

from .models import ActivityMembership, Role


@admin.register(ActivityMembership)
class ActivityMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "activity", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "activity")
    search_fields = ("user__username", "user__email", "activity__name")
    raw_id_fields = ("user", "activity")
    ordering = ("user__username", "activity__name")

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "activity":
            field.help_text = "Obligatoire sauf pour le rôle Gérant global."
        return field
