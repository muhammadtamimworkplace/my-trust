from django.shortcuts import render

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


def home(request):
    """Public landing page: hero with search, how it works, scam categories."""
    return render(request, "core/home.html", {"scam_categories": SCAM_CATEGORIES})
