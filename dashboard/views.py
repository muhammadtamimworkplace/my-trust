from django.core.paginator import Paginator
from django.shortcuts import render

from accounts.decorators import admin_required

from .services import overview_stats, report_queue

REPORTS_PER_PAGE = 15


@admin_required
def overview(request):
    """Admin home: totals and scam-pattern statistics."""
    return render(request, "dashboard/overview.html", {"section": "overview", **overview_stats()})


@admin_required
def report_queue_view(request):
    """Reports to review, filtered by status tab."""
    reports, tabs, active = report_queue(request.GET.get("status", ""))
    page_obj = Paginator(reports, REPORTS_PER_PAGE).get_page(request.GET.get("page"))
    context = {
        "section": "queue", "page_obj": page_obj, "tabs": tabs, "active_tab": active,
        "query_string": f"status={active}",
    }
    return render(request, "dashboard/report_queue.html", context)
