from django.shortcuts import render

from accounts.decorators import admin_required

from .services import overview_stats


@admin_required
def overview(request):
    """Admin home: totals and scam-pattern statistics."""
    return render(request, "dashboard/overview.html", {"section": "overview", **overview_stats()})
