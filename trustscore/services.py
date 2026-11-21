"""Trust score calculation (guide §9).

A transparent, rule-based heuristic, not a statistical model. Principles:
  1. Unverified reports (allegations) never change the score.
  2. Only admin-verified (APPROVED) reports apply a penalty.
  3. Community feedback is opinion; it sets the base score.
  4. No label ever says "fraud": the strongest label is "Use caution".
"""
import math

from django.db.models import Count, Q

from feedback.models import Feedback
from reports.models import ScamReport

from .models import TrustEvaluation

Label = TrustEvaluation.Label

# All tuning constants live here, so the thesis can state and justify them in one place.
PENALTY_PER_VERIFIED_REPORT = 15   # points removed per admin-verified report
MAX_VERIFIED_PENALTY = 60          # verified reports can remove at most this many points
MIN_FEEDBACK_FOR_RATING = 3        # below this (and no verified reports): "Not enough data"
CAUTION_BELOW = 40                 # score < 40           -> Use caution
GOOD_FROM = 70                     # score >= 70          -> Good reputation; between -> Mixed


def round_half_up(value):
    """Round .5 upwards (12.5 -> 13). Python's round() uses banker's rounding (12.5 -> 12)."""
    return math.floor(value + 0.5)


def calculate_score(positive, negative, verified_reports):
    """Return (score 0–100, label) from visible feedback counts and verified report count.

        community_ratio = (P + 1) / (P + N + 2)       # Laplace smoothing: 0.5 with no data
        score = clamp(round(100 * ratio - min(15 * V, 60)), 0, 100)

    Worked example: P=8, N=2, V=1 -> ratio 9/12 = 0.75 -> 75 - 15 = 60 -> Mixed reputation.
    """
    if min(positive, negative, verified_reports) < 0:
        raise ValueError("Counts cannot be negative.")

    community_ratio = (positive + 1) / (positive + negative + 2)
    penalty = min(PENALTY_PER_VERIFIED_REPORT * verified_reports, MAX_VERIFIED_PENALTY)
    score = max(0, min(100, round_half_up(100 * community_ratio - penalty)))

    if positive + negative < MIN_FEEDBACK_FOR_RATING and verified_reports == 0:
        label = Label.INSUFFICIENT
    elif score < CAUTION_BELOW:
        label = Label.CAUTION
    elif score < GOOD_FROM:
        label = Label.MIXED
    else:
        label = Label.GOOD
    return score, label


UNVERIFIED_STATUSES = [ScamReport.Status.PENDING, ScamReport.Status.NEEDS_EVIDENCE]


def recalculate_trust(page):
    """Rebuild and save the TrustEvaluation snapshot for one page (2 count queries + 1 write).

    Call this after anything that changes a page's feedback or report statuses.
    Hidden feedback is excluded; rejected reports count for nothing.
    """
    feedback = Feedback.objects.filter(page=page, is_hidden=False).aggregate(
        positive=Count("pk", filter=Q(sentiment=Feedback.Sentiment.POSITIVE)),
        negative=Count("pk", filter=Q(sentiment=Feedback.Sentiment.NEGATIVE)),
    )
    reports = ScamReport.objects.filter(page=page).aggregate(
        verified=Count("pk", filter=Q(status=ScamReport.Status.APPROVED)),
        pending=Count("pk", filter=Q(status__in=UNVERIFIED_STATUSES)),
    )
    score, label = calculate_score(feedback["positive"], feedback["negative"], reports["verified"])
    trust, _ = TrustEvaluation.objects.update_or_create(
        page=page,
        defaults={
            "score": score,
            "label": label,
            "positive_count": feedback["positive"],
            "negative_count": feedback["negative"],
            "verified_report_count": reports["verified"],
            "pending_report_count": reports["pending"],
        },
    )
    return trust
