from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import AdminAction
from feedback.models import Comment, Feedback, FeedbackVote
from reports.models import Evidence, FacebookPage, ScamReport
from trustscore.models import TrustEvaluation

User = get_user_model()
MODELS = [User, FacebookPage, ScamReport, Feedback, Comment, FeedbackVote, TrustEvaluation, AdminAction]


class AdminSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser("boss", "boss@example.com", "x")
        page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.report = ScamReport.objects.create(
            page=page, reporter=cls.superuser, category="OTHER",
            title="Something went wrong", description="A detailed description of what happened here.",
        )
        TrustEvaluation.objects.create(page=page)
        cls.action = AdminAction.objects.create(admin=cls.superuser, action_type="APPROVE_REPORT", report=cls.report)

    def setUp(self):
        self.client.force_login(self.superuser)

    def admin_url(self, model, view, *args):
        return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{view}", args=args)

    def test_every_domain_model_is_registered(self):
        for model in MODELS:
            with self.subTest(model=model.__name__):
                self.assertTrue(admin.site.is_registered(model))
        self.assertFalse(admin.site.is_registered(Evidence), "Evidence is managed inline under its report")

    def test_every_changelist_loads(self):
        for model in MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(self.client.get(self.admin_url(model, "changelist")).status_code, 200)

    def test_report_change_page_loads_with_evidence_inline(self):
        response = self.client.get(self.admin_url(ScamReport, "change", self.report.pk))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evidence files")

    def test_trust_evaluations_cannot_be_added(self):
        self.assertEqual(self.client.get(self.admin_url(TrustEvaluation, "add")).status_code, 403)

    def test_audit_log_cannot_be_added_changed_or_deleted(self):
        self.assertEqual(self.client.get(self.admin_url(AdminAction, "add")).status_code, 403)
        self.assertEqual(self.client.get(self.admin_url(AdminAction, "delete", self.action.pk)).status_code, 403)
        response = self.client.post(self.admin_url(AdminAction, "change", self.action.pk), {"note": "tampered"})
        self.assertEqual(response.status_code, 403)
        self.action.refresh_from_db()
        self.assertEqual(self.action.note, "")

    def test_evidence_inline_lists_files_without_public_media_links(self):
        import shutil
        import tempfile

        from reports.tests.helpers import png_upload

        media = tempfile.mkdtemp(prefix="mytrust-admin-media-")
        try:
            with self.settings(MEDIA_ROOT=media):
                evidence = Evidence.objects.create(report=self.report, file=png_upload("receipt.png"))
                response = self.client.get(self.admin_url(ScamReport, "change", self.report.pk))
        finally:
            shutil.rmtree(media, ignore_errors=True)
        self.assertContains(response, "receipt.png")
        self.assertContains(response, evidence.file.name)     # shown as text ("stored as")
        self.assertNotContains(response, f"/media/{evidence.file.name}")  # never a public link
