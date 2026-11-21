from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ReportForm
from .services import submit_report

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
            return redirect("accounts:profile")  # report detail page arrives in P5-T04
    else:
        form = ReportForm()
    return render(request, "reports/report_form.html", {"form": form})
