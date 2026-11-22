"""Business logic for community feedback."""
from django.core.exceptions import ValidationError
from django.db import transaction

from trustscore.services import recalculate_trust

from .models import Feedback, FeedbackVote


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


def delete_feedback(feedback):
    """Delete a feedback entry (and its votes) and refresh the page's trust snapshot."""
    page = feedback.page
    with transaction.atomic():
        feedback.delete()
        recalculate_trust(page)


def vote_on_feedback(*, user, feedback, value):
    """Like (+1) or dislike (-1) someone else's feedback, as a toggle.

    - same vote again  -> removes it
    - opposite vote    -> switches it
    - no vote yet      -> creates it
    Returns the user's vote after the call: 1, -1, or None (removed).
    Votes never affect the trust score.
    """
    if value not in (FeedbackVote.Value.LIKE, FeedbackVote.Value.DISLIKE):
        raise ValidationError("Invalid vote.")
    if feedback.user_id == user.pk:
        raise ValidationError("You cannot vote on your own feedback.")
    if feedback.is_hidden:
        raise ValidationError("This feedback is not available.")

    with transaction.atomic():
        existing = FeedbackVote.objects.filter(feedback=feedback, user=user).first()
        if existing is None:
            FeedbackVote.objects.create(feedback=feedback, user=user, value=value)
            return value
        if existing.value == value:
            existing.delete()
            return None
        existing.value = value
        existing.save(update_fields=["value"])
        return value
