from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from reports.models import ScamReport

from .forms import ReviewForm
from .services import decide_report, overview_stats, report_queue, search_users, toggle_user_active

User = get_user_model()
REPORTS_PER_PAGE = 15
USERS_PER_PAGE = 20


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


@admin_required
def report_review(request, pk):
    """Review one report: read it, see the evidence, decide."""
    report = get_object_or_404(
        ScamReport.objects.select_related("page__trust", "reporter").prefetch_related("evidence"), pk=pk
    )
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                decide_report(admin=request.user, report=report,
                              decision=form.cleaned_data["decision"], note=form.cleaned_data["note"])
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                messages.success(request, f"Decision saved: {report.get_status_display()}.")
                return redirect("dashboard:report_queue")
    else:
        form = ReviewForm()

    context = {
        "section": "queue", "report": report, "form": form,
        "evidence_list": report.evidence.all(),
        "history": report.admin_actions.select_related("admin"),
    }
    return render(request, "dashboard/report_review.html", context)


@admin_required
def user_list(request):
    """All users with search and an activate/deactivate button."""
    query = request.GET.get("q", "").strip()
    page_obj = Paginator(search_users(query), USERS_PER_PAGE).get_page(request.GET.get("page"))
    context = {"section": "users", "page_obj": page_obj, "q": query, "query_string": urlencode({"q": query}) if query else ""}
    return render(request, "dashboard/user_list.html", context)


@admin_required
@require_POST
def user_toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    try:
        now_active = toggle_user_active(admin=request.user, target=target)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.success(request, f"{target.username} is now {'active' if now_active else 'deactivated'}.")
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return redirect(next_url)
    return redirect("dashboard:user_list")
