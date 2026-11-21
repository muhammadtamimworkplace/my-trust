from django.conf import settings
from django.db import models

from reports.models import ScamReport


class AdminAction(models.Model):
    """Audit log entry for one administrator decision (guide §8.2, FR-23).

    Reports and users are linked with real foreign keys. Feedback and comments are
    referenced by type + id, so the log does not depend on those tables. Entries are
    kept even if the target is later deleted (the link is simply cleared).
    """

    class ActionType(models.TextChoices):
        APPROVE_REPORT = "APPROVE_REPORT", "Approved report"
        REJECT_REPORT = "REJECT_REPORT", "Rejected report"
        REQUEST_EVIDENCE = "REQUEST_EVIDENCE", "Requested more evidence"
        HIDE_FEEDBACK = "HIDE_FEEDBACK", "Hid feedback"
        UNHIDE_FEEDBACK = "UNHIDE_FEEDBACK", "Restored feedback"
        HIDE_COMMENT = "HIDE_COMMENT", "Hid comment"
        UNHIDE_COMMENT = "UNHIDE_COMMENT", "Restored comment"
        ACTIVATE_USER = "ACTIVATE_USER", "Activated user"
        DEACTIVATE_USER = "DEACTIVATE_USER", "Deactivated user"

    class TargetType(models.TextChoices):
        FEEDBACK = "FEEDBACK", "Feedback"
        COMMENT = "COMMENT", "Comment"

    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="admin_actions")
    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    report = models.ForeignKey(
        ScamReport, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_actions"
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="admin_actions_received",
    )
    target_type = models.CharField(max_length=20, choices=TargetType.choices, blank=True)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "admin action"

    def __str__(self):
        return f"{self.admin} · {self.get_action_type_display()} · {self.created_at:%Y-%m-%d %H:%M}"
