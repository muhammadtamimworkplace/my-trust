"""Business logic for community feedback."""
from django.db import transaction

from trustscore.services import recalculate_trust

from .models import Feedback


def save_feedback(*, user, page, sentiment, comment=""):
    """Create the user's feedback on a page, or update it (one per user per page).

    Editing never changes `is_hidden`: a moderator's decision stays in force.
    The page's trust snapshot is refreshed in the same transaction.
    Returns (feedback, created).
    """
    with transaction.atomic():
        feedback, created = Feedback.objects.update_or_create(
            page=page, user=user, defaults={"sentiment": sentiment, "comment": comment.strip()},
        )
        recalculate_trust(page)
    return feedback, created
