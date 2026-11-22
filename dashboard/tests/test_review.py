from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from dashboard.models import AdminAction
from dashboard.services import decide_report
from reports.models import Evidence, FacebookPage, ScamReport
from reports.tests.helpers import TempMediaMixin, png_upload
from trustscore.models import TrustEvaluation

User = get_user_model()
S = ScamReport.Status
A = AdminAction.ActionType


class ReviewBase(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.other_admin = User.objects.create_user("mod2", "mod2@example.com", "x", role=User.Role.ADMIN)
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def setUp(self):
        self.report = ScamReport.objects.create(
            page=self.page, reporter=self.user, category="ADVANCE_PAYMENT", status=S.PENDING,
            title="Paid in advance, never received", description="Paid by bKash and the seller blocked me.",
        )
        self.url = reverse("dashboard:report_review", args=[self.report.pk])


class DecideReportServiceTests(ReviewBase):
    def test_approve_sets_status_logs_action_and_raises_verified_count(self):
        decide_report(admin=self.admin, report=self.report, decision="approve", note="Receipt matches.")
        self.report.refresh_from_db()
        self.assertEqual((self.report.status, self.report.admin_note), (S.APPROVED, "Receipt matches."))
        self.assertIsNotNone(self.report.reviewed_at)
        action = AdminAction.objects.get()
        self.assertEqual((action.admin, action.action_type, action.report, action.note), (self.admin, A.APPROVE_REPORT, self.report, "Receipt matches."))
        trust = TrustEvaluation.objects.get(page=self.page)
        self.assertEqual((trust.verified_report_count, trust.pending_report_count, trust.score), (1, 0, 35))

    def test_reject_and_request_evidence(self):
        decide_report(admin=self.admin, report=self.report, decision="reject", note="Not enough proof.")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, S.REJECTED)
        decide_report(admin=self.admin, report=self.report, decision="request_evidence", note="Send the receipt.")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, S.NEEDS_EVIDENCE)
        self.assertEqual(list(AdminAction.objects.order_by("id").values_list("action_type", flat=True)),
                         [A.REJECT_REPORT, A.REQUEST_EVIDENCE])

    def test_decision_can_be_changed_and_score_follows(self):
        decide_report(admin=self.admin, report=self.report, decision="approve")
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).verified_report_count, 1)
        decide_report(admin=self.admin, report=self.report, decision="reject", note="Found to be a mistake.")
        trust = TrustEvaluation.objects.get(page=self.page)
        self.assertEqual((trust.verified_report_count, trust.score), (0, 50))
        self.assertEqual(AdminAction.objects.count(), 2)

    def test_note_is_required_to_reject_or_request_evidence_but_not_to_approve(self):
        for decision in ("reject", "request_evidence"):
            with self.subTest(decision=decision), self.assertRaises(ValidationError):
                decide_report(admin=self.admin, report=self.report, decision=decision, note="   ")
        decide_report(admin=self.admin, report=self.report, decision="approve", note="")
        self.assertEqual(AdminAction.objects.count(), 1)

    def test_unknown_decision_is_rejected(self):
        with self.assertRaises(ValidationError):
            decide_report(admin=self.admin, report=self.report, decision="delete_everything", note="x")

    def test_admin_cannot_review_own_report(self):
        own = ScamReport.objects.create(page=self.page, reporter=self.admin, category="OTHER",
                                        title="My own report title", description="A description that is long enough.")
        with self.assertRaises(ValidationError):
            decide_report(admin=self.admin, report=own, decision="approve")
        own.refresh_from_db()
        self.assertEqual(own.status, S.PENDING)

    @override_settings(EVIDENCE_MAX_FILES=1)
    def test_cannot_request_more_evidence_when_report_is_at_the_file_limit(self):
        Evidence.objects.create(report=self.report, file=png_upload())
        with self.assertRaises(ValidationError) as ctx:
            decide_report(admin=self.admin, report=self.report, decision="request_evidence", note="More please")
        self.assertIn("maximum of 1 evidence files", ctx.exception.messages[0])

    def test_everything_rolls_back_if_the_audit_entry_fails(self):
        with mock.patch.object(AdminAction.objects, "create", side_effect=RuntimeError("db down")):
            with self.assertRaises(RuntimeError):
                decide_report(admin=self.admin, report=self.report, decision="approve")
        self.report.refresh_from_db()
        self.assertEqual((self.report.status, self.report.reviewed_at), (S.PENDING, None))
        self.assertEqual(TrustEvaluation.objects.count(), 0)


class ReviewViewTests(ReviewBase):
    def setUp(self):
        super().setUp()
        Evidence.objects.create(report=self.report, file=png_upload("receipt.png"))
        self.client.force_login(self.admin)

    def test_page_shows_report_evidence_form_and_empty_history(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paid in advance, never received")
        self.assertContains(response, "receipt.png")
        self.assertContains(response, reverse("reports:evidence_file", args=[self.report.evidence.get().pk]))
        self.assertContains(response, "No decisions yet.")

    def test_posting_a_decision_saves_it_and_returns_to_queue(self):
        response = self.client.post(self.url, {"decision": "approve", "note": "Verified."}, follow=True)
        self.assertRedirects(response, reverse("dashboard:report_queue"))
        self.assertContains(response, "Decision saved: Verified by admin.")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, S.APPROVED)

    def test_form_errors_keep_the_report_unchanged(self):
        for data, text in (({"decision": "reject", "note": ""}, "Write a note for the reporter"),
                           ({"note": "no decision"}, "This field is required."),
                           ({"decision": "nuke", "note": "x"}, "Select a valid choice")):
            with self.subTest(data=data):
                self.assertContains(self.client.post(self.url, data), text)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, S.PENDING)
        self.assertEqual(AdminAction.objects.count(), 0)

    def test_service_rule_errors_are_shown_on_the_form(self):
        own = ScamReport.objects.create(page=self.page, reporter=self.admin, category="OTHER",
                                        title="My own report title", description="A description that is long enough.")
        response = self.client.post(reverse("dashboard:report_review", args=[own.pk]), {"decision": "approve"})
        self.assertContains(response, "You cannot review your own report.")

    def test_history_lists_previous_decisions(self):
        self.client.post(self.url, {"decision": "request_evidence", "note": "Add the receipt"})
        response = self.client.get(self.url)
        self.assertContains(response, "Requested more evidence")
        self.assertContains(response, "by mod")

    def test_reporter_sees_the_note_after_the_decision(self):
        self.client.post(self.url, {"decision": "request_evidence", "note": "Please add the receipt."})
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("reports:report_detail", args=[self.report.pk])), "Please add the receipt.")
        self.assertContains(self.client.get(reverse("reports:my_reports")), "Please add the receipt.")

    def test_access_control_and_csrf(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {"decision": "approve"}).status_code, 403)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.admin)
        self.assertEqual(strict.post(self.url, {"decision": "approve"}).status_code, 403)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, S.PENDING)

    def test_unknown_report_is_404(self):
        self.assertEqual(self.client.get(reverse("dashboard:report_review", args=[99999])).status_code, 404)

    def test_queue_rows_link_to_review_page(self):
        self.assertContains(self.client.get(reverse("dashboard:report_queue")), f'href="{self.url}"')
