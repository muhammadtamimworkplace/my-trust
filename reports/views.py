from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from feedback.forms import FeedbackForm
from feedback.models import Feedback

from .forms import AddEvidenceForm, PageSearchForm, ReportForm
from .models import Evidence, FacebookPage, ScamReport
from .services import (
    add_requested_evidence,
    page_has_public_info,
    page_overview,
    reports_by_user,
    search_pages,
    submit_report,
)

EVIDENCE_CONTENT_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
REPORTS_PER_PAGE = 10
PAGES_PER_PAGE = 12

REPORT_FIELDS = ("category", "title", "description", "incident_date", "amount_lost")


def page_list(request):
    """Public search over reported Facebook pages (name or link, category, verification)."""
    form = PageSearchForm(request.GET or None)
    filters = form.cleaned_data if form.is_valid() else {}
    pages = search_pages(filters.get("q", ""), filters.get("category", ""), filters.get("status", ""))
    page_obj = Paginator(pages, PAGES_PER_PAGE).get_page(request.GET.get("page"))

    query = request.GET.copy()
    query.pop("page", None)
    context = {
        "form": form,
        "page_obj": page_obj,
        "query_string": query.urlencode(),
        "is_filtered": any(filters.values()),
    }
    return render(request, "reports/page_list.html", context)


def page_detail(request, pk):
    """One Facebook page: trust badge, verified reports, unverified allegations and feedback.

    Pages without public information (only rejected reports, no visible feedback)
    return 404, matching the page list, except for administrators.
    """
    page = get_object_or_404(FacebookPage.objects.select_related("trust"), pk=pk)
    if not page_has_public_info(page) and not (request.user.is_authenticated and request.user.is_platform_admin):
        raise Http404("Page not found.")

    my_feedback = None
    if request.user.is_authenticated:
        my_feedback = Feedback.objects.filter(page=page, user=request.user).first()
    context = {
        "page": page,
        "my_feedback": my_feedback,
        "feedback_form": FeedbackForm(instance=my_feedback) if request.user.is_authenticated else None,
        **page_overview(page),
    }
    return render(request, "reports/page_detail.html", context)


@login_required
def report_create(request):
    """Report a Facebook page. The report starts as 'Under review'.

    `?page=<id>` pre-fills the page name and link ("Report this page" button).
    """
    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            report = submit_report(
                reporter=request.user,
                page_name=data["page_name"],
                page_url=data["page_url"],
                report_data={field: data[field] for field in REPORT_FIELDS},
                evidence_files=data["evidence"],
            )
            messages.success(
                request,
                f"Thank you. Your report about “{report.page.name}” was submitted and is now under review.",
            )
            return redirect("reports:report_detail", pk=report.pk)
    else:
        initial = {}
        page_id = request.GET.get("page", "")
        if page_id.isdigit():
            page = FacebookPage.objects.filter(pk=page_id).first()
            if page:
                initial = {"page_name": page.name, "page_url": page.url}
        form = ReportForm(initial=initial)
    return render(request, "reports/report_form.html", {"form": form})


def report_detail(request, pk):
    """One report. Rejected reports return 404 to everyone except the reporter and admins,
    so their existence is not revealed. Evidence and the admin note are private."""
    report = get_object_or_404(ScamReport.objects.select_related("page__trust", "reporter"), pk=pk)
    if not report.is_visible_to(request.user):
        raise Http404("Report not found.")
    can_manage = report.is_managed_by(request.user)
    context = {
        "report": report,
        "can_manage": can_manage,
        "evidence_list": report.evidence.all() if can_manage else [],
    }
    return render(request, "reports/report_detail.html", context)


@login_required
def evidence_add(request, pk):
    """Reporter uploads extra evidence after an admin requested it (NEEDS_EVIDENCE)."""
    report = get_object_or_404(ScamReport.objects.select_related("page"), pk=pk)
    if report.reporter_id != request.user.pk:
        raise PermissionDenied("Only the reporter can add evidence to this report.")
    if report.status != ScamReport.Status.NEEDS_EVIDENCE:
        messages.info(request, "More evidence can only be added when an administrator asks for it.")
        return redirect("reports:report_detail", pk=report.pk)

    attached = report.evidence.count()
    remaining = settings.EVIDENCE_MAX_FILES - attached
    if request.method == "POST":
        form = AddEvidenceForm(request.POST, request.FILES, already_attached=attached)
        if form.is_valid():
            add_requested_evidence(report, form.cleaned_data["evidence"])
            messages.success(request, "Thank you. Your new evidence was added and the report is back under review.")
            return redirect("reports:report_detail", pk=report.pk)
    else:
        form = AddEvidenceForm(already_attached=attached)
    context = {"report": report, "form": form, "attached": attached, "remaining": remaining}
    return render(request, "reports/evidence_add.html", context)


@never_cache
@login_required
def evidence_file(request, pk):
    """Serve one evidence image to its reporter or an administrator only.

    Evidence is never exposed through a public /media/ URL (it may contain phone
    numbers or payment details). never_cache stops browsers/proxies keeping copies.
    """
    evidence = get_object_or_404(Evidence.objects.select_related("report"), pk=pk)
    if not evidence.report.is_managed_by(request.user):
        raise PermissionDenied("You are not allowed to view this evidence.")
    extension = evidence.file.name.rsplit(".", 1)[-1].lower()
    try:
        handle = evidence.file.open("rb")
    except FileNotFoundError:
        raise Http404("Evidence file is missing.")
    response = FileResponse(handle, content_type=EVIDENCE_CONTENT_TYPES.get(extension, "application/octet-stream"))
    response["Content-Disposition"] = "inline"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def my_reports(request):
    """The logged-in user's own reports with their review status."""
    page_obj = Paginator(reports_by_user(request.user), REPORTS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "reports/my_reports.html", {"page_obj": page_obj})
