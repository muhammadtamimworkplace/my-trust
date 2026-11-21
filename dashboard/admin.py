from django.contrib import admin

from .models import AdminAction


@admin.register(AdminAction)
class AdminActionAdmin(admin.ModelAdmin):
    """The audit log is append-only: entries can be viewed but never added, edited or deleted here."""

    list_display = ("created_at", "admin", "action_type", "report", "target_user", "target_type", "target_id")
    list_filter = ("action_type", "created_at")
    search_fields = ("admin__username", "note", "report__title", "target_user__username")
    # No date_hierarchy (needs MariaDB time-zone tables); see reports/admin.py.
    list_select_related = ("admin", "report", "target_user")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
