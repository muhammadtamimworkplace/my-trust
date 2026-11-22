from django.shortcuts import render

from feedback.models import Feedback
from reports.models import ScamReport

Category = ScamReport.Category

# Landing-page presentation for each scam category. Titles come from the model
# (ScamReport.Category), so categories are defined in exactly one place.
CATEGORY_PRESENTATION = {
    Category.ADVANCE_PAYMENT: ("bi-cash-coin", "The seller demands full payment before delivery, then disappears."),
    Category.NON_DELIVERY: ("bi-box-seam", "Paid orders never arrive, and messages go unanswered."),
    Category.FAKE_PRODUCT: ("bi-image", "Photos show one product; a cheap copy or something else arrives."),
    Category.IMPERSONATION: ("bi-person-badge", "A page copies a well-known brand's name and logo to look genuine."),
    Category.HARASSMENT: ("bi-chat-left-dots", "Buyers who complain are threatened, insulted or blocked."),
}

SCAM_CATEGORIES = [
    {"icon": icon, "title": category.label, "text": text}
    for category, (icon, text) in CATEGORY_PRESENTATION.items()
]


RECENT_REPORTS = 3
RECENT_FEEDBACK = 5


def recent_activity():
    """Latest public community activity for the landing page.

    Only admin-verified reports (never unverified allegations or rejected ones) and
    visible feedback are shown, by username only.
    """
    verified_reports = (
        ScamReport.objects.filter(status=ScamReport.Status.APPROVED)
        .select_related("page").order_by("-created_at")[:RECENT_REPORTS]
    )
    feedback = (
        Feedback.objects.filter(is_hidden=False)
        .select_related("page", "user").order_by("-created_at")[:RECENT_FEEDBACK]
    )
    return {"recent_verified_reports": verified_reports, "recent_feedback": feedback}


def home(request):
    """Public landing page: hero with search, how it works, community activity, scam categories."""
    return render(request, "core/home.html", {"scam_categories": SCAM_CATEGORIES, **recent_activity()})
