from django.core.validators import MaxValueValidator
from django.db import models

from reports.models import FacebookPage


class TrustEvaluation(models.Model):
    """Stored snapshot of a page's trust score (guide §9).

    Deliberately denormalized: it is derived from reports and feedback, and kept
    so that lists can sort/filter by score cheaply. It is only ever rebuilt by
    trustscore.services.recalculate_trust() (P6-T02), never edited by hand.

    Labels never say "fraud": unverified reports are allegations, and even the
    worst label only advises caution.
    """

    class Label(models.TextChoices):
        INSUFFICIENT = "INSUFFICIENT", "Not enough data"
        GOOD = "GOOD", "Good reputation"
        MIXED = "MIXED", "Mixed reputation"
        CAUTION = "CAUTION", "Use caution"

    page = models.OneToOneField(FacebookPage, on_delete=models.CASCADE, related_name="trust")
    score = models.PositiveSmallIntegerField(default=50, validators=[MaxValueValidator(100)])
    label = models.CharField(max_length=20, choices=Label.choices, default=Label.INSUFFICIENT)
    positive_count = models.PositiveIntegerField(default=0, help_text="Visible positive feedback.")
    negative_count = models.PositiveIntegerField(default=0, help_text="Visible negative feedback.")
    verified_report_count = models.PositiveIntegerField(default=0, help_text="Reports approved by an admin.")
    pending_report_count = models.PositiveIntegerField(default=0, help_text="Unverified allegations under review.")
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "trust evaluation"
        constraints = [
            models.CheckConstraint(condition=models.Q(score__lte=100), name="trust_score_at_most_100"),
        ]

    def __str__(self):
        return f"{self.page}: {self.score} ({self.get_label_display()})"
