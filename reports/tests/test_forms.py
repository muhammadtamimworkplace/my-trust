import io
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from PIL import Image

from reports.forms import ReportForm


def png(name="shot.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


VALID_DATA = {
    "page_name": "  Example Shop ",
    "page_url": "m.facebook.com/Example.Shop/?ref=share",
    "category": "ADVANCE_PAYMENT",
    "title": "Paid in advance, never received",
    "description": "I paid 2,500 BDT by bKash for a dress. The seller blocked me afterwards.",
    "incident_date": "",
    "amount_lost": "2500",
}


class ReportFormTests(TestCase):
    """TestCase (not SimpleTestCase): ModelForm validation also checks DB constraints (amount_lost >= 0)."""

    def make_form(self, files=None, **overrides):
        files = [png()] if files is None else files
        return ReportForm(data={**VALID_DATA, **overrides}, files=MultiValueDict({"evidence": files}))

    def test_valid_form_normalizes_url_and_name(self):
        form = self.make_form()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["page_url"], "https://www.facebook.com/example.shop")
        self.assertEqual(form.cleaned_data["page_name"], "Example Shop")
        self.assertEqual(len(form.cleaned_data["evidence"]), 1)

    def test_several_files_are_accepted(self):
        form = self.make_form(files=[png("a.png"), png("b.png"), png("c.png")])
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["evidence"]), 3)

    def test_at_least_one_screenshot_is_required(self):
        form = self.make_form(files=[])
        self.assertFalse(form.is_valid())
        self.assertIn("evidence", form.errors)

    @override_settings(EVIDENCE_MAX_FILES=2)
    def test_too_many_files_are_rejected(self):
        form = self.make_form(files=[png("a.png"), png("b.png"), png("c.png")])
        self.assertFalse(form.is_valid())
        self.assertIn("at most 2 files", form.errors["evidence"][0])

    def test_invalid_file_error_names_the_file(self):
        fake = SimpleUploadedFile("receipt.png", b"definitely not an image", content_type="image/png")
        form = self.make_form(files=[png("good.png"), fake])
        self.assertFalse(form.is_valid())
        self.assertTrue(any(msg.startswith("receipt.png:") for msg in form.errors["evidence"]))

    def test_non_facebook_link_is_rejected(self):
        form = self.make_form(page_url="https://www.instagram.com/example.shop")
        self.assertFalse(form.is_valid())
        self.assertIn("page_url", form.errors)

    def test_model_validation_rules_apply(self):
        cases = {
            "title": {"title": "short"},
            "description": {"description": "Too short to be useful."},
            "incident_date": {"incident_date": (timezone.localdate() + timedelta(days=2)).isoformat()},
            "amount_lost": {"amount_lost": "-10"},
            "category": {"category": "SOMETHING_ELSE"},
        }
        for field, overrides in cases.items():
            with self.subTest(field=field):
                form = self.make_form(**overrides)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_status_and_reporter_cannot_be_submitted_through_the_form(self):
        self.assertNotIn("status", ReportForm.base_fields)
        self.assertNotIn("reporter", ReportForm.base_fields)
        self.assertNotIn("admin_note", ReportForm.base_fields)

    def test_fields_render_in_logical_order_with_multi_file_input(self):
        form = ReportForm()
        self.assertEqual(list(form.fields)[:3], ["page_name", "page_url", "category"])
        self.assertEqual(list(form.fields)[-1], "evidence")
        html = str(form["evidence"])
        self.assertIn("multiple", html)
        self.assertIn('accept=".jpg,.jpeg,.png', html)
