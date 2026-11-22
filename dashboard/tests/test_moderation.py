from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import AdminAction
from dashboard.services import toggle_content_hidden
from feedback.models import Comment, Feedback
from reports.models import FacebookPage, ScamReport
from trustscore.models import TrustEvaluation
from trustscore.services import recalculate_trust

User = get_user_model()
A = AdminAction.ActionType
URL = reverse("dashboard:moderation")


class ModerationBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.author = User.objects.create_user("author", "author@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.report = ScamReport.objects.create(
            page=cls.page, reporter=cls.author, category="OTHER", status=ScamReport.Status.APPROVED,
            title="A report title here", description="A description that is long enough to be valid.",
        )
        users = [User.objects.create_user(f"neg{i}", f"neg{i}@example.com", "x") for i in range(3)]
        cls.feedbacks = [Feedback.objects.create(page=cls.page, user=u, sentiment="NEGATIVE", comment=f"Rude text {i}")
                         for i, u in enumerate(users)]
        cls.comment = Comment.objects.create(report=cls.report, user=cls.author, body="Offensive comment body")
        recalculate_trust(cls.page)


class ToggleContentServiceTests(ModerationBase):
    def test_hiding_feedback_logs_action_and_recalculates_trust(self):
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).negative_count, 3)
        self.assertTrue(toggle_content_hidden(admin=self.admin, kind="feedback", pk=self.feedbacks[0].pk))
        self.feedbacks[0].refresh_from_db()
        self.assertTrue(self.feedbacks[0].is_hidden)
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).negative_count, 2)
        action = AdminAction.objects.get()
        self.assertEqual((action.action_type, action.target_type, action.target_id, action.target_user, action.admin),
                         (A.HIDE_FEEDBACK, "FEEDBACK", self.feedbacks[0].pk, self.feedbacks[0].user, self.admin))

    def test_restoring_feedback_brings_the_count_back(self):
        toggle_content_hidden(admin=self.admin, kind="feedback", pk=self.feedbacks[0].pk)
        self.assertFalse(toggle_content_hidden(admin=self.admin, kind="feedback", pk=self.feedbacks[0].pk))
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).negative_count, 3)
        self.assertEqual(list(AdminAction.objects.order_by("id").values_list("action_type", flat=True)),
                         [A.HIDE_FEEDBACK, A.UNHIDE_FEEDBACK])

    def test_hiding_a_comment_is_logged_with_its_report_and_does_not_touch_trust(self):
        before = TrustEvaluation.objects.get(page=self.page).score
        toggle_content_hidden(admin=self.admin, kind="comment", pk=self.comment.pk)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_hidden)
        action = AdminAction.objects.get()
        self.assertEqual((action.action_type, action.target_type, action.report), (A.HIDE_COMMENT, "COMMENT", self.report))
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).score, before)

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(ValidationError):
            toggle_content_hidden(admin=self.admin, kind="report", pk=1)


class ModerationViewTests(ModerationBase):
    def setUp(self):
        self.client.force_login(self.admin)

    def toggle_url(self, kind, pk):
        return reverse("dashboard:moderation_toggle", args=[kind, pk])

    def test_lists_show_feedback_by_default_and_comments_on_tab(self):
        self.assertContains(self.client.get(URL), "Rude text 0")
        self.assertNotContains(self.client.get(URL), "Offensive comment body")
        self.assertContains(self.client.get(URL, {"type": "comment"}), "Offensive comment body")
        self.assertContains(self.client.get(URL, {"type": "anything-else"}), "Rude text 0")

    def test_hide_from_the_page_removes_it_from_public_views(self):
        self.client.post(self.toggle_url("feedback", self.feedbacks[0].pk), {"next": URL}, follow=True)
        public = Client()
        detail = public.get(reverse("reports:page_detail", args=[self.page.pk]))
        self.assertNotContains(detail, "Rude text 0")
        self.assertContains(detail, "Rude text 1")
        self.assertContains(self.client.get(URL), "Hidden")

    def test_hidden_comment_disappears_from_report_page_and_can_be_restored(self):
        self.client.post(self.toggle_url("comment", self.comment.pk))
        report_page = reverse("reports:report_detail", args=[self.report.pk])
        self.assertNotContains(Client().get(report_page), "Offensive comment body")
        self.client.post(self.toggle_url("comment", self.comment.pk))
        self.assertContains(Client().get(report_page), "Offensive comment body")

    def test_success_message_and_safe_redirect(self):
        response = self.client.post(self.toggle_url("feedback", self.feedbacks[0].pk), {"next": f"{URL}?type=feedback"}, follow=True)
        self.assertContains(response, "The feedback is now hidden.")
        offsite = self.client.post(self.toggle_url("feedback", self.feedbacks[1].pk), {"next": "https://evil.example/"})
        self.assertRedirects(offsite, URL, fetch_redirect_response=False)

    def test_unknown_kind_or_id_is_404(self):
        self.assertEqual(self.client.post(self.toggle_url("report", 1)).status_code, 404)
        self.assertEqual(self.client.post(self.toggle_url("feedback", 99999)).status_code, 404)

    def test_access_control_get_only_and_csrf(self):
        url = self.toggle_url("feedback", self.feedbacks[0].pk)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.admin)
        self.assertEqual(strict.post(url).status_code, 403)
        self.feedbacks[0].refresh_from_db()
        self.assertFalse(self.feedbacks[0].is_hidden)
