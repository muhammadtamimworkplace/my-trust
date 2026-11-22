"""Queries and actions behind the admin dashboard."""
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from feedback.models import Comment, Feedback
from reports.models import FacebookPage, ScamReport

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
