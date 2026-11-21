from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from reports.models import Evidence, FacebookPage, ScamReport
from reports.services import add_requested_evidence

from .helpers import TempMediaMixin, png_upload

User = get_user_model()
S = ScamReport.Status


class AddEvidenceTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner", "owner@example.com", "x")
        cls.stranger = User.objects.create_user("stranger", "stranger@example.com", "x")
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def setUp(self):
        self.report = ScamReport.objects.create(
            page=self.page, reporter=self.owner, category="NON_DELIVERY", status=S.NEEDS_EVIDENCE,
            admin_note="Please upload the payment receipt.", title="Parcel never delivered",
            description="I paid in advance and the parcel never arrived at my home.",
        )
        Evidence.objects.create(report=self.report, file=png_upload("first.png"))
        self.url = reverse("reports:evidence_add", args=[self.report.pk])
        self.detail = reverse("reports:report_detail", args=[self.report.pk])
        self.client.force_login(self.owner)

    def test_owner_sees_request_and_button_on_report_page(self):
        response = self.client.get(self.detail)
        self.assertContains(response, "More evidence requested.")
        self.assertContains(response, f'href="{self.url}"')

    def test_form_shows_admin_request_and_remaining_slots(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please upload the payment receipt.")
        self.assertContains(response, "you can add up to 4 more")

    def test_upload_attaches_files_and_sends_report_back_to_review(self):
        response = self.client.post(self.url, {"evidence": [png_upload("receipt.png")]}, follow=True)
        self.assertRedirects(response, self.detail)
        self.assertContains(response, "back under review")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, S.PENDING)
        self.assertEqual([e.original_name for e in self.report.evidence.all()], ["first.png", "receipt.png"])

    @override_settings(EVIDENCE_MAX_FILES=2)
    def test_total_file_limit_counts_existing_evidence(self):
        response = self.client.post(self.url, {"evidence": [png_upload("a.png"), png_upload("b.png")]})
        self.assertContains(response, "at most 2 files per report (1 more allowed).")
        self.assertEqual(self.report.evidence.count(), 1)

    def test_empty_upload_is_rejected(self):
        response = self.client.post(self.url, {})
        self.assertContains(response, "Attach at least one screenshot.")

    def test_other_users_and_admins_cannot_add_evidence(self):
        for user in (self.stranger, self.admin):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 403)
                self.assertEqual(self.client.post(self.url, {"evidence": [png_upload()]}).status_code, 403)
        self.assertEqual(self.report.evidence.count(), 1)

    def test_not_allowed_unless_evidence_was_requested(self):
        for status in (S.PENDING, S.APPROVED, S.REJECTED):
            with self.subTest(status=status):
                ScamReport.objects.filter(pk=self.report.pk).update(status=status)
                response = self.client.post(self.url, {"evidence": [png_upload()]}, follow=True)
                self.assertRedirects(response, self.detail)
                self.assertContains(response, "only be added when an administrator asks")
        self.assertEqual(self.report.evidence.count(), 1)

    def test_service_refuses_wrong_status(self):
        self.report.status = S.APPROVED
        with self.assertRaises(ValueError):
            add_requested_evidence(self.report, [png_upload()])

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")
