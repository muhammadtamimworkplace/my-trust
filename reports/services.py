"""Business logic for reports (kept out of views so it can be tested directly)."""
import logging

from django.db import transaction
from django.db.models import Count

from .models import Evidence, FacebookPage, ScamReport

logger = logging.getLogger(__name__)


def reports_by_user(user):
    """A user's own reports, newest first, with page and evidence count loaded in the
    same query (no extra query per row)."""
    return (
        ScamReport.objects.filter(reporter=user)
        .select_related("page")
        .annotate(evidence_count=Count("evidence"))
        .order_by("-created_at")
    )


def save_evidence_files(report, files):
    """Attach uploaded files to a report. Must run inside a transaction.

    If anything fails, every file already written to storage is removed (a database
    rollback alone would leave them behind), then the error is re-raised. This also
    covers the evidence whose own save failed after its file was written.
    """
    attempted = []
    try:
        for upload in files:
            evidence = Evidence(report=report, file=upload, original_name=upload.name[:255])
            attempted.append(evidence)
            evidence.save()
    except Exception:
        for evidence in attempted:
            stored_name = evidence.file.name or ""
            if stored_name.startswith("evidence/"):  # assigned by upload_to => written to storage
                evidence.file.storage.delete(stored_name)
        logger.exception("Saving evidence for report %s failed; stored files removed", report.pk)
        raise
    return attempted


def add_requested_evidence(report, evidence_files):
    """Attach extra evidence to a report in NEEDS_EVIDENCE and send it back to review (PENDING).

    Callers check permissions (reporter only); this enforces the status rule.
    """
    if report.status != ScamReport.Status.NEEDS_EVIDENCE:
        raise ValueError("Evidence can only be added when an administrator has requested it.")
    with transaction.atomic():
        save_evidence_files(report, evidence_files)
        report.status = ScamReport.Status.PENDING
        report.save(update_fields=["status", "updated_at"])
    logger.info("Report %s: %d evidence file(s) added, back to review", report.pk, len(evidence_files))
    return report


def submit_report(*, reporter, page_name, page_url, report_data, evidence_files):
    """Create a scam report (status PENDING) with its evidence, atomically.

    `page_url` must already be canonical (ReportForm.clean_page_url). An existing
    page with that URL is reused and keeps its original name, so the same page is
    never stored twice. Trust-score recalculation is added in P6-T02.
    """
    with transaction.atomic():
        page, created = FacebookPage.objects.get_or_create(
            url=page_url, defaults={"name": page_name, "created_by": reporter}
        )
        report = ScamReport.objects.create(page=page, reporter=reporter, **report_data)
        save_evidence_files(report, evidence_files)

    logger.info("Report %s submitted for page %s (new page: %s)", report.pk, page.pk, created)
    return report
