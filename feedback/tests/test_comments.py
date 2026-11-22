from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from feedback.models import Comment
from reports.models import FacebookPage, ScamReport

User = get_user_model()
S = ScamReport.Status


class CommentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("commenter", "commenter@example.com", "x")
        cls.owner = User.objects.create_user("owner", "owner@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def make_report(self, status=S.APPROVED):
        return ScamReport.objects.create(
            page=self.page, reporter=self.owner, category="OTHER", status=status,
            title="A report title here", description="A description that is long enough to be valid.",
        )

    def urls(self, report):
        return reverse("feedback:comment_create", args=[report.pk]), reverse("reports:report_detail", args=[report.pk])

    def test_logged_in_user_can_comment_on_public_reports(self):
        self.client.force_login(self.user)
        for status in (S.APPROVED, S.PENDING, S.NEEDS_EVIDENCE):
            with self.subTest(status=status):
                report = self.make_report(status)
                post_url, detail = self.urls(report)
                response = self.client.post(post_url, {"body": "  Same thing happened to me.  "}, follow=True)
                self.assertRedirects(response, detail)
                self.assertContains(response, "Your comment was posted.")
                self.assertEqual(report.comments.get().body, "Same thing happened to me.")

    def test_comments_are_listed_by_username_and_hidden_ones_are_not(self):
        report = self.make_report()
        Comment.objects.create(report=report, user=self.user, body="Visible comment")
        Comment.objects.create(report=report, user=self.user, body="Moderated comment", is_hidden=True)
        response = self.client.get(self.urls(report)[1])
        self.assertContains(response, "Visible comment")
        self.assertContains(response, "commenter")
        self.assertNotContains(response, "Moderated comment")
        self.assertNotContains(response, "commenter@example.com")
        self.assertContains(response, "Comments (1)")

    def test_rejected_report_cannot_be_commented_on_and_has_no_comment_section(self):
        report = self.make_report(S.REJECTED)
        post_url, detail = self.urls(report)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(post_url, {"body": "Hello there"}).status_code, 404)
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(detail), "Comments (")
        self.assertEqual(Comment.objects.count(), 0)

    def test_invalid_comments_are_rejected(self):
        report = self.make_report()
        post_url, _ = self.urls(report)
        self.client.force_login(self.user)
        for body in ("", "x", "y" * 1001):
            with self.subTest(length=len(body)):
                response = self.client.post(post_url, {"body": body}, follow=True)
                self.assertContains(response, "alert-danger")
        self.assertEqual(Comment.objects.count(), 0)

    def test_visitors_see_login_prompt_and_cannot_post(self):
        report = self.make_report()
        post_url, detail = self.urls(report)
        self.assertContains(self.client.get(detail), "to join the discussion")
        self.assertNotContains(self.client.get(detail), "Post comment")
        self.assertEqual(self.client.post(post_url, {"body": "Hello there"}).status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_html_in_comment_is_escaped_and_csrf_enforced(self):
        report = self.make_report()
        post_url, detail = self.urls(report)
        self.client.force_login(self.user)
        self.client.post(post_url, {"body": "<script>alert(1)</script> hi"})
        page = self.client.get(detail)
        self.assertNotContains(page, "<script>alert(1)")
        self.assertContains(page, "&lt;script&gt;")
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(post_url, {"body": "No token here"}).status_code, 403)
        self.assertEqual(Comment.objects.count(), 1)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.urls(self.make_report())[0]).status_code, 405)
