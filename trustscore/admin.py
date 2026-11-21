from django.contrib import admin

from .models import TrustEvaluation


@admin.register(TrustEvaluation)
class TrustEvaluationAdmin(admin.ModelAdmin):
    """Read-only: scores are derived data, rebuilt only by trustscore.services."""

    list_display = ("page", "score", "label", "verified_report_count", "pending_report_count",
                    "positive_count", "negative_count", "calculated_at")
    list_filter = ("label",)
    search_fields = ("page__name", "page__url")
    list_select_related = ("page",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
