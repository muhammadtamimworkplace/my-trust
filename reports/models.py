import uuid
from pathlib import PurePath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.validators import EVIDENCE_VALIDATORS

from .utils import normalize_facebook_url


def validate_not_in_future(value):
    if value and value > timezone.localdate():
        raise ValidationError("The incident date cannot be in the future.", code="future_date")


class FacebookPage(models.Model):
    """A Facebook sales page that has been reported or reviewed on My Trust.

    `url` is always stored in canonical form (see normalize_facebook_url), so the
    unique constraint stops the same page from being added twice under different links.
    """

    name = models.CharField(max_length=150, db_index=True)
    url = models.URLField("Facebook URL", max_length=255, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pages_added",
        help_text="User who first added this page (kept even if that account is later removed).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Facebook page"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.url = normalize_facebook_url(self.url)
        super().save(*args, **kwargs)


class ScamReport(models.Model):
    """A user's complaint about a Facebook page.

    A report is only an *allegation* until an administrator approves it
    (status APPROVED, shown as "Verified by admin"). Unverified reports never
    affect a page's trust score (guide §9).
    """

    class Category(models.TextChoices):
        ADVANCE_PAYMENT = "ADVANCE_PAYMENT", "Advance payment"
        NON_DELIVERY = "NON_DELIVERY", "Non-delivery"
        FAKE_PRODUCT = "FAKE_PRODUCT", "Fake product"
        IMPERSONATION = "IMPERSONATION", "Impersonation"
        HARASSMENT = "HARASSMENT", "Harassment"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Under review"
        NEEDS_EVIDENCE = "NEEDS_EVIDENCE", "Needs more evidence"
        APPROVED = "APPROVED", "Verified by admin"
        REJECTED = "REJECTED", "Rejected"

    page = models.ForeignKey(FacebookPage, on_delete=models.PROTECT, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reports")
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=150, validators=[MinLengthValidator(10)])
    description = models.TextField(validators=[MinLengthValidator(30), MaxLengthValidator(5000)])
    incident_date = models.DateField(null=True, blank=True, validators=[validate_not_in_future])
    amount_lost = models.DecimalField(
        "amount lost (BDT)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    admin_note = models.TextField(blank=True, help_text="Latest note from the reviewing administrator (shown to the reporter).")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "scam report"
        indexes = [
            models.Index(fields=["page", "status"], name="report_page_status_idx"),
            models.Index(fields=["status", "created_at"], name="report_status_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_lost__isnull=True) | models.Q(amount_lost__gte=0),
                name="report_amount_lost_not_negative",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.page})"

    @property
    def is_verified(self):
        return self.status == self.Status.APPROVED

    @property
    def is_public(self):
        """Rejected reports are hidden from the public; all others are shown
        (unverified ones clearly labelled as allegations)."""
        return self.status != self.Status.REJECTED

    def is_managed_by(self, user):
        """The reporter and platform admins may see private details (evidence, admin note)."""
        return user.is_authenticated and (user.pk == self.reporter_id or user.is_platform_admin)

    def is_visible_to(self, user):
        return self.is_public or self.is_managed_by(user)


def evidence_upload_path(instance, filename):
    """Store evidence as evidence/<year>/<month>/<random uuid>.<ext>.

    The user's filename is never used on disk (it is kept in original_name for
    display only), so names cannot be guessed or used to overwrite other files.
    """
    extension = PurePath(filename).suffix.lower().lstrip(".")
    if extension == "jpeg":
        extension = "jpg"
    today = timezone.localdate()
    return f"evidence/{today:%Y}/{today:%m}/{uuid.uuid4().hex}.{extension}"


class Evidence(models.Model):
    """A screenshot supporting a scam report.

    Evidence can contain personal data (phone numbers, payment IDs), so it is
    never served publicly: only the reporter and administrators may view it
    (access-controlled view in P5-T05).
    """

    report = models.ForeignKey(ScamReport, on_delete=models.CASCADE, related_name="evidence")
    file = models.ImageField(upload_to=evidence_upload_path, validators=EVIDENCE_VALIDATORS)
    original_name = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "evidence file"
        verbose_name_plural = "evidence files"

    def __str__(self):
        return self.original_name or self.file.name

    def save(self, *args, **kwargs):
        if self.file and not self.pk:
            self.original_name = (self.original_name or PurePath(self.file.name).name)[:255]
            self.size_bytes = self.file.size
        super().save(*args, **kwargs)
