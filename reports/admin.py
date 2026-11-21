from django.contrib import admin
from django.template.defaultfilters import filesizeformat

from .models import Evidence, FacebookPage, ScamReport


@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "created_by", "created_at")
    search_fields = ("name", "url")
    readonly_fields = ("created_by", "created_at", "updated_at")


class EvidenceInline(admin.TabularInline):
    """Evidence is listed but not linked: files are not served from public /media/ URLs.
    Viewing goes through the access-controlled evidence view (P5-T05)."""

    model = Evidence
    extra = 0
    can_delete = True
    fields = ("original_name", "stored_as", "size", "uploaded_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="stored as")
    def stored_as(self, obj):
        return obj.file.name

    @admin.display(description="size")
    def size(self, obj):
        return filesizeformat(obj.size_bytes)


@admin.register(ScamReport)
class ScamReportAdmin(admin.ModelAdmin):
    list_display = ("title", "page", "category", "status", "reporter", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("title", "description", "page__name", "page__url", "reporter__username")
    autocomplete_fields = ("page", "reporter")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
    # No date_hierarchy: it needs MariaDB time-zone tables (CONVERT_TZ), which are not
    # loaded on this server. The created_at list filter covers the same need.
    inlines = [EvidenceInline]
    list_select_related = ("page", "reporter")
