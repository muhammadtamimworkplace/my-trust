from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from core.forms import BootstrapFormMixin
from core.validators import ALLOWED_IMAGE_EXTENSIONS, EVIDENCE_VALIDATORS

from .models import ScamReport
from .utils import normalize_facebook_url


class MultipleFileInput(forms.ClearableFileInput):
    """File input that lets the user pick several files at once."""

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """A FileField that accepts a list of files (pattern from Django's file-upload docs)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)] if data else []


def validate_evidence_files(files, already_attached=0):
    """Run every upload check on each file and enforce the per-report file limit.

    Errors name the offending file so the user knows which one to replace.
    """
    limit = settings.EVIDENCE_MAX_FILES
    if already_attached + len(files) > limit:
        remaining = limit - already_attached
        raise ValidationError(
            f"You can attach at most {limit} files per report"
            + (f" ({remaining} more allowed)." if already_attached else "."),
            code="too_many_files",
        )
    errors = []
    for upload in files:
        for validator in EVIDENCE_VALIDATORS:
            try:
                validator(upload)
            except ValidationError as exc:
                errors.extend(f"{upload.name}: {message}" for message in exc.messages)
                break
    if errors:
        raise ValidationError(errors)


ACCEPT_ATTRIBUTE = ",".join(f".{ext}" for ext in ALLOWED_IMAGE_EXTENSIONS) + ",image/jpeg,image/png"


class EvidenceUploadMixin(forms.Form):
    evidence = MultipleFileField(
        label="Screenshots / evidence",
        help_text=(
            f"JPG or PNG, up to {settings.EVIDENCE_MAX_BYTES // (1024 * 1024)} MB each, at most "
            f"{settings.EVIDENCE_MAX_FILES} files. Payment receipts and chat screenshots help admins verify your report. "
            "Evidence is visible only to you and administrators."
        ),
        widget=MultipleFileInput(attrs={"accept": ACCEPT_ATTRIBUTE}),
    )

    already_attached = 0

    def clean_evidence(self):
        files = self.cleaned_data["evidence"]
        if not files:
            raise ValidationError("Attach at least one screenshot.", code="required")
        validate_evidence_files(files, self.already_attached)
        return files


class ReportForm(BootstrapFormMixin, EvidenceUploadMixin, forms.ModelForm):
    """Report a Facebook page. The page itself is found or created from its link (P5-T02)."""

    page_name = forms.CharField(
        label="Facebook page name", max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Trendy Closet"}),
    )
    page_url = forms.CharField(
        label="Facebook page link", max_length=500,
        help_text="Copy the link from your browser or the Facebook app, e.g. https://www.facebook.com/example.shop",
        widget=forms.TextInput(attrs={"placeholder": "https://www.facebook.com/…", "inputmode": "url"}),
    )

    field_order = ["page_name", "page_url", "category", "title", "description", "incident_date", "amount_lost", "evidence"]

    class Meta:
        model = ScamReport
        fields = ["category", "title", "description", "incident_date", "amount_lost"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "incident_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "amount_lost": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }
        help_texts = {
            "title": "A short summary, at least 10 characters.",
            "description": "What happened? Include dates, amounts and how you paid (30–5000 characters).",
            "incident_date": "Optional. When did it happen?",
            "amount_lost": "Optional. Leave empty if you lost no money.",
        }

    def clean_page_name(self):
        return self.cleaned_data["page_name"].strip()

    def clean_page_url(self):
        # Store and compare the canonical form, so different links to the same page match.
        return normalize_facebook_url(self.cleaned_data["page_url"])
