from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from reports.models import Evidence, FacebookPage, ScamReport

from .helpers import TempMediaMixin, png_upload

User = get_user_model()
S = ScamReport.Status


class ReportDetailTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner", "owner-private@example.com", "x")
        cls.stranger = User.objects.create_user("stranger", "stranger@example.com", "x")
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def make(self, status, **extra):
        report = ScamReport.objects.create(
            page=self.page, reporter=self.owner, category=ScamReport.Category.ADVANCE_PAYMENT, status=status,
            title="Paid in advance, never received", admin_note=extra.pop("admin_note", "Private reviewer note"),
            description="I paid 2,500 BDT by bKash.\nThe seller blocked me afterwards.", **extra,
        )
        Evidence.objects.create(report=report, file=png_upload("receipt.png"))
        return report

    def get(self, report, user=None):
        self.client.logout()
        if user:
            self.client.force_login(user)
        return self.client.get(reverse("reports:report_detail", args=[report.pk]))

    def test_verified_report_is_public_with_verified_banner(self):
        response = self.get(self.make(S.APPROVED))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verified by admin.")
        self.assertNotContains(response, "Unverified allegation.")

    def test_pending_and_needs_evidence_are_public_but_labelled_unverified(self):
        for status in (S.PENDING, S.NEEDS_EVIDENCE):
            with self.subTest(status=status):
                response = self.get(self.make(status))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Unverified allegation.")
                self.assertContains(response, "does not affect the page's trust score")

    def test_rejected_report_is_404_for_visitors_and_other_users(self):
        report = self.make(S.REJECTED)
        self.assertEqual(self.get(report).status_code, 404)
        self.assertEqual(self.get(report, self.stranger).status_code, 404)

    def test_rejected_report_is_visible_to_owner_and_admin(self):
        report = self.make(S.REJECTED)
        for user in (self.owner, self.admin):
            with self.subTest(user=user.username):
                response = self.get(report, user)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "This report is not shown publicly")

    def test_evidence_and_admin_note_are_private(self):
        report = self.make(S.APPROVED)
        for user in (None, self.stranger):
            with self.subTest(user=getattr(user, "username", "anonymous")):
                response = self.get(report, user)
                self.assertNotContains(response, "receipt.png")
                self.assertNotContains(response, "Private reviewer note")
                self.assertNotContains(response, "Private to you and administrators")
        for user in (self.owner, self.admin):
            with self.subTest(user=user.username):
                response = self.get(report, user)
                self.assertContains(response, "receipt.png")
                self.assertContains(response, "Private reviewer note")

    def test_reporter_shown_by_username_never_email(self):
        response = self.get(self.make(S.APPROVED))
        self.assertContains(response, "owner")
        self.assertNotContains(response, "owner-private@example.com")

    def test_description_line_breaks_kept_and_html_escaped(self):
        report = self.make(S.APPROVED)
        report.description = "Line one <script>alert('x')</script>\nLine two"
        report.save()
        response = self.get(report)
        self.assertNotContains(response, "<script>alert")
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "<br>")

    def test_external_page_link_is_safe(self):
        response = self.get(self.make(S.APPROVED))
        self.assertContains(response, 'href="https://www.facebook.com/example.shop" target="_blank" rel="noopener noreferrer nofollow"')

    def test_unknown_report_is_404(self):
        self.assertEqual(self.client.get(reverse("reports:report_detail", args=[99999])).status_code, 404)

    def test_my_reports_rows_link_to_detail(self):
        report = self.make(S.PENDING)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("reports:my_reports"))
        self.assertContains(response, f'href="{reverse("reports:report_detail", args=[report.pk])}"')
