from django.shortcuts import render

# Scam categories explained on the landing page. They match the report
# categories planned for ScamReport (guide §8.2); the model becomes the single
# source of truth in P4-T02, and this list will then read from it.
SCAM_CATEGORIES = [
    {
        "icon": "bi-cash-coin",
        "title": "Advance payment",
        "text": "The seller demands full payment before delivery, then disappears.",
    },
    {
        "icon": "bi-box-seam",
        "title": "Non-delivery",
        "text": "Paid orders never arrive, and messages go unanswered.",
    },
    {
        "icon": "bi-image",
        "title": "Fake product",
        "text": "Photos show one product; a cheap copy or something else arrives.",
    },
    {
        "icon": "bi-person-badge",
        "title": "Impersonation",
        "text": "A page copies a well-known brand's name and logo to look genuine.",
    },
    {
        "icon": "bi-chat-left-dots",
        "title": "Harassment",
        "text": "Buyers who complain are threatened, insulted or blocked.",
    },
]


def home(request):
    """Public landing page: hero with search, how it works, scam categories."""
    return render(request, "core/home.html", {"scam_categories": SCAM_CATEGORIES})
