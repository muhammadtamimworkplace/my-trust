from django import forms

from core.forms import BootstrapFormMixin

from .services import DECISIONS


class ReviewForm(BootstrapFormMixin, forms.Form):
    """Administrator's decision on a report, with a note to the reporter."""

    decision = forms.ChoiceField(
        label="Decision",
        choices=[
            ("approve", "Approve: verified by admin"),
            ("reject", "Reject: not a scam or not enough proof"),
            ("request_evidence", "Request more evidence"),
        ],
        widget=forms.RadioSelect,
    )
    note = forms.CharField(
        label="Note to the reporter", required=False, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Required for Reject and Request more evidence. Shown to the reporter.",
    )

    def clean(self):
        cleaned = super().clean()
        decision, note = cleaned.get("decision"), (cleaned.get("note") or "").strip()
        if decision in DECISIONS and DECISIONS[decision][2] and not note:
            self.add_error("note", "Write a note for the reporter explaining this decision.")
        return cleaned
