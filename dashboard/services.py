"""Queries and actions behind the admin dashboard."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from feedback.models import Comment, Feedback
from reports.models import FacebookPage, ScamReport
from trustscore.services import recalculate_trust

from .models import AdminAction

User = get_user_model()
S = ScamReport.Status

TOP_PAGES = 5


def with_percent(rows, total):
    """Add a `percent` (0–100, whole number) to each row dict, for progress bars."""
    for row in rows:
        row["percent"] = round(100 * row["total"] / total) if total else 0
    return rows


def overview_stats():
    """Everything the overview page shows, in a handful of aggregate queries."""
    by_status = dict(ScamReport.objects.values_list("status").annotate(n=Count("pk")))
    total_reports = sum(by_status.values())

    status_rows = [
        {"label": label, "status": value, "total": by_status.get(value, 0)} for value, label in S.choices
    ]

    category_counts = {
        row["category"]: row
        for row in ScamReport.objects.values("category").annotate(
            total=Count("pk"), verified=Count("pk", filter=Q(status=S.APPROVED)),
        )
    }
    category_rows = [
        {
            "label": label, "category": value,
            "total": category_counts.get(value, {}).get("total", 0),
            "verified": category_counts.get(value, {}).get("verified", 0),
        }
        for value, label in ScamReport.Category.choices
    ]

    top_pages = (
        FacebookPage.objects.select_related("trust")
        .annotate(
            public_reports=Count("reports", filter=~Q(reports__status=S.REJECTED)),
            verified_reports=Count("reports", filter=Q(reports__status=S.APPROVED)),
        )
        .filter(public_reports__gt=0)
        .order_by("-public_reports", "-verified_reports", "name")[:TOP_PAGES]
    )

    return {
        "totals": {
            "users": User.objects.count(),
            "pages": FacebookPage.objects.count(),
            "reports": total_reports,
            "feedback": Feedback.objects.count(),
            "comments": Comment.objects.count(),
        },
        "awaiting_review": by_status.get(S.PENDING, 0),
        "status_rows": with_percent(status_rows, total_reports),
        "category_rows": with_percent(category_rows, total_reports),
        "top_pages": top_pages,
    }


QUEUE_TABS = [
    ("PENDING", "Under review"),
    ("NEEDS_EVIDENCE", "Needs evidence"),
    ("APPROVED", "Verified"),
    ("REJECTED", "Rejected"),
    ("ALL", "All"),
]
DEFAULT_QUEUE_TAB = "PENDING"


def report_queue(tab):
    """Reports for one queue tab plus the count shown on every tab.

    "Under review" is listed oldest first (first in, first out); other tabs newest first.
    Returns (queryset, [(tab_value, label, count), ...], active_tab).
    """
    counts = dict(ScamReport.objects.values_list("status").annotate(n=Count("pk")))
    counts["ALL"] = sum(counts.values())
    tabs = [(value, label, counts.get(value, 0)) for value, label in QUEUE_TABS]

    valid = {value for value, _ in QUEUE_TABS}
    active = tab if tab in valid else DEFAULT_QUEUE_TAB

    reports = ScamReport.objects.select_related("page", "reporter").annotate(evidence_count=Count("evidence"))
    if active != "ALL":
        reports = reports.filter(status=active)
    reports = reports.order_by("created_at" if active == S.PENDING else "-created_at")
    return reports, tabs, active


DECISIONS = {
    # decision -> (new report status, audit action, note required?)
    "approve": (S.APPROVED, AdminAction.ActionType.APPROVE_REPORT, False),
    "reject": (S.REJECTED, AdminAction.ActionType.REJECT_REPORT, True),
    "request_evidence": (S.NEEDS_EVIDENCE, AdminAction.ActionType.REQUEST_EVIDENCE, True),
}


def decide_report(*, admin, report, decision, note=""):
    """Apply an administrator's decision to a report.

    Atomically: new status + note + review time, an audit-log entry, and a refreshed
    trust score for the page. Raises ValidationError for rule violations:
      - unknown decision, or a missing note where one is required
      - the admin reviewing their own report (conflict of interest)
      - requesting evidence when the report already has the maximum number of files
    """
    if decision not in DECISIONS:
        raise ValidationError("Choose a decision.")
    new_status, action_type, note_required = DECISIONS[decision]
    note = (note or "").strip()
    if note_required and not note:
        raise ValidationError("Write a note for the reporter explaining this decision.")
    if report.reporter_id == admin.pk:
        raise ValidationError("You cannot review your own report. Ask another administrator.")
    if decision == "request_evidence" and report.evidence.count() >= settings.EVIDENCE_MAX_FILES:
        raise ValidationError(
            f"This report already has the maximum of {settings.EVIDENCE_MAX_FILES} evidence files, "
            "so more cannot be requested. Approve or reject it instead."
        )

    with transaction.atomic():
        report.status = new_status
        report.admin_note = note
        report.reviewed_at = timezone.now()
        report.save(update_fields=["status", "admin_note", "reviewed_at", "updated_at"])
        AdminAction.objects.create(admin=admin, action_type=action_type, report=report, note=note)
        recalculate_trust(report.page)
    return report


def search_users(query=""):
    """Users for the management list, newest first, with their report counts.

    `query` matches username, email, first or last name (case-insensitive, partial).
    """
    users = User.objects.annotate(report_count=Count("reports")).order_by("-date_joined", "-pk")
    query = (query or "").strip()
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
            | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    return users


def toggle_user_active(*, admin, target):
    """Activate or deactivate an account and log it. Returns the new `is_active` value.

    Refused for yourself (you would lock yourself out) and for superusers (managed
    only through Django admin). A deactivated user cannot log in, and Django rejects
    their existing sessions on the next request.
    """
    if target.pk == admin.pk:
        raise ValidationError("You cannot deactivate your own account.")
    if target.is_superuser:
        raise ValidationError("Superuser accounts can only be changed in the Django admin.")

    with transaction.atomic():
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        AdminAction.objects.create(
            admin=admin, target_user=target,
            action_type=AdminAction.ActionType.ACTIVATE_USER if target.is_active else AdminAction.ActionType.DEACTIVATE_USER,
        )
    return target.is_active
