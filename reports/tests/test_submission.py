from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from reports.models import Evidence, FacebookPage, ScamReport
from reports.services import submit_report

from .helpers import VALID_REPORT_POST, TempMediaMixin, png_upload

User = get_user_model()
URL = reverse("reports:report_create")
REPORT_DATA = {
    "category": "ADVANCE_PAYMENT", "title": "Paid in advance, never received",
    "description": "I paid 2,500 BDT by bKash for a dress. The seller blocked me afterwards.",
    "incident_date": None, "amount_lost": None,
}


class SubmitReportServiceTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("reporter", "reporter@example.com", "x")

    def submit(self, url="https://www.facebook.com/example.shop", name="Example Shop", files=None):
        return submit_report(
            reporter=self.user, page_name=name, page_url=url, report_data=REPORT_DATA,
            evidence_files=files if files is not None else [png_upload()],
        )

    def test_creates_page_report_and_evidence(self):
        report = self.submit(files=[png_upload("a.png"), png_upload("b.png")])
        self.assertEqual(report.status, ScamReport.Status.PENDING)
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.page.created_by, self.user)
        self.assertEqual([e.original_name for e in report.evidence.all()], ["a.png", "b.png"])

    def test_existing_page_is_reused_and_keeps_its_name(self):
        first = self.submit(name="Example Shop")
        second = self.submit(name="Different Name For Same Page")
        self.assertEqual(first.page, second.page)
        self.assertEqual(FacebookPage.objects.count(), 1)
        self.assertEqual(second.page.name, "Example Shop")

    def test_failure_while_saving_evidence_rolls_everything_back_including_files(self):
        real_save = Evidence.save
        stored = []  # paths of files written to storage

        def save_then_fail_on_second(evidence, *args, **kwargs):
            real_save(evidence, *args, **kwargs)  # writes the file, inserts the row
            stored.append(Path(self._temp_media, evidence.file.name))
            if len(stored) == 2:
                raise OSError("database went away after the file was written")

        with mock.patch.object(Evidence, "save", autospec=True, side_effect=save_then_fail_on_second):
            with self.assertRaises(OSError):
                self.submit(files=[png_upload("a.png"), png_upload("b.png")])

        self.assertEqual((FacebookPage.objects.count(), ScamReport.objects.count(), Evidence.objects.count()), (0, 0, 0))
        self.assertEqual(len(stored), 2)
        self.assertFalse(any(path.exists() for path in stored), "orphaned evidence files left on disk")


class ReportCreateViewTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("reporter", "reporter@example.com", "x")

    def setUp(self):
        self.client.force_login(self.user)

    def post(self, files=None, **overrides):
        data = {**VALID_REPORT_POST, **overrides, "evidence": files if files is not None else [png_upload()]}
        return self.client.post(URL, data)

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(URL), f"{reverse('accounts:login')}?next={URL}")

    def test_form_page_renders_as_multipart(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/report_form.html")
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_valid_submission_creates_pending_report_and_shows_message(self):
        response = self.client.post(URL, {**VALID_REPORT_POST, "evidence": [png_upload()]}, follow=True)
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertContains(response, "is now under review")
        report = ScamReport.objects.get()
        self.assertEqual((report.reporter, report.status), (self.user, ScamReport.Status.PENDING))
        self.assertEqual(report.page.url, "https://www.facebook.com/example.shop")
        self.assertEqual(report.evidence.count(), 1)

    def test_status_reporter_and_admin_fields_cannot_be_injected(self):
        other = User.objects.create_user("victim", "victim@example.com", "x")
        self.post(status="APPROVED", reporter=other.pk, admin_note="approved by me", reviewed_at="2026-01-01")
        report = ScamReport.objects.get()
        self.assertEqual(report.status, ScamReport.Status.PENDING)
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.admin_note, "")
        self.assertIsNone(report.reviewed_at)

    def test_invalid_submission_shows_errors_and_saves_nothing(self):
        response = self.post(page_url="https://example.com/not-facebook", files=[])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a facebook.com link")
        self.assertContains(response, "Attach at least one screenshot.")
        self.assertEqual((FacebookPage.objects.count(), ScamReport.objects.count()), (0, 0))

    def test_post_without_csrf_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(URL, {**VALID_REPORT_POST, "evidence": [png_upload()]})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ScamReport.objects.count(), 0)

    def test_navbar_links_to_report_page(self):
        self.assertContains(self.client.get(reverse("core:home")), f'href="{URL}"')
