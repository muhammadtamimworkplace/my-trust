from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from .forms import ReportForm
from .models import Evidence, ScamReport

EVIDENCE_CONTENT_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
from .services import reports_by_user, submit_report

REPORTS_PER_PAGE = 10

REPORT_FIELDS = ("category", "title", "description", "incident_date", "amount_lost")


@login_required
def report_create(request):
    """Report a Facebook page. The report starts as 'Under review'."""
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
        form = ReportForm()
    return render(request, "reports/report_form.html", {"form": form})


def report_detail(request, pk):
    """One report. Rejected reports return 404 to everyone except the reporter and admins,
    so their existence is not revealed. Evidence and the admin note are private."""
    report = get_object_or_404(ScamReport.objects.select_related("page", "reporter"), pk=pk)
    if not report.is_visible_to(request.user):
        raise Http404("Report not found.")
    can_manage = report.is_managed_by(request.user)
    context = {
        "report": report,
        "can_manage": can_manage,
        "evidence_list": report.evidence.all() if can_manage else [],
    }
    return render(request, "reports/report_detail.html", context)


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
