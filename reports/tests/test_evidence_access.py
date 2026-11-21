from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from reports.models import Evidence, FacebookPage, ScamReport

from .helpers import TempMediaMixin, png_upload

User = get_user_model()


class EvidenceAccessTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner", "owner@example.com", "x")
        cls.stranger = User.objects.create_user("stranger", "stranger@example.com", "x")
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.report = ScamReport.objects.create(
            page=page, reporter=cls.owner, category="ADVANCE_PAYMENT", status=ScamReport.Status.APPROVED,
            title="Paid in advance, never received", description="Paid by bKash, then the seller blocked me.",
        )

    def setUp(self):
        self.evidence = Evidence.objects.create(report=self.report, file=png_upload("receipt.png"))
        self.url = reverse("reports:evidence_file", args=[self.evidence.pk])

    def test_anonymous_visitor_is_sent_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_other_user_is_forbidden_even_for_a_public_verified_report(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_owner_and_admin_receive_the_image_with_private_headers(self):
        for user in (self.owner, self.admin):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "image/png")
                self.assertEqual(response["Content-Disposition"], "inline")
                self.assertIn("no-store", response["Cache-Control"])
                self.assertIn("private", response["Cache-Control"])
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                body = b"".join(response.streaming_content)
                self.assertTrue(body.startswith(b"\x89PNG"))

    def test_public_media_url_is_not_served(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(f"/media/{self.evidence.file.name}").status_code, 404)

    def test_missing_file_on_disk_returns_404(self):
        Path(self._temp_media, self.evidence.file.name).unlink()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_unknown_evidence_returns_404(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("reports:evidence_file", args=[99999])).status_code, 404)

    def test_report_page_shows_thumbnails_to_owner_only(self):
        detail = reverse("reports:report_detail", args=[self.report.pk])
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(detail), f'src="{self.url}"')
        self.client.force_login(self.stranger)
        self.assertNotContains(self.client.get(detail), self.url)
