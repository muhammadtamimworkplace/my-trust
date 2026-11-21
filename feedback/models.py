from django.conf import settings
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

from reports.models import FacebookPage, ScamReport


class Feedback(models.Model):
    """A registered user's overall opinion of a Facebook page.

    This is community *opinion*, shown separately from admin-verified reports.
    Each user can give at most one feedback per page (they can edit it).
    """

    class Sentiment(models.TextChoices):
        POSITIVE = "POSITIVE", "Positive"
        NEGATIVE = "NEGATIVE", "Negative"

    page = models.ForeignKey(FacebookPage, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_given")
    sentiment = models.CharField(max_length=10, choices=Sentiment.choices)
    comment = models.TextField(blank=True, validators=[MaxLengthValidator(1000)])
    is_hidden = models.BooleanField(default=False, help_text="Hidden by a moderator; excluded from the trust score.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "feedback"
        constraints = [
            models.UniqueConstraint(fields=["page", "user"], name="feedback_one_per_user_per_page"),
        ]

    def __str__(self):
        return f"{self.get_sentiment_display()} feedback on {self.page} by {self.user}"


class Comment(models.Model):
    """A discussion comment under a scam report."""

    report = models.ForeignKey(ScamReport, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField(validators=[MinLengthValidator(2), MaxLengthValidator(1000)])
    is_hidden = models.BooleanField(default=False, help_text="Hidden by a moderator.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user} on report #{self.report_id}"


class FeedbackVote(models.Model):
    """A like (+1) or dislike (-1) on someone else's feedback; one vote per user."""

    class Value(models.IntegerChoices):
        LIKE = 1, "Like"
        DISLIKE = -1, "Dislike"

    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_votes")
    value = models.SmallIntegerField(choices=Value.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["feedback", "user"], name="vote_one_per_user_per_feedback"),
            models.CheckConstraint(condition=models.Q(value__in=[1, -1]), name="vote_value_like_or_dislike"),
        ]

    def __str__(self):
        return f"{self.get_value_display()} by {self.user} on feedback #{self.feedback_id}"
