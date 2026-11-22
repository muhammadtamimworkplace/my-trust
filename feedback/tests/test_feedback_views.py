from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from feedback.models import Feedback
from reports.models import FacebookPage, ScamReport
from trustscore.models import TrustEvaluation

User = get_user_model()


class FeedbackSaveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "x")
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        ScamReport.objects.create(
            page=cls.page, reporter=cls.user, category="OTHER", status=ScamReport.Status.PENDING,
            title="A report title here", description="A description that is long enough to be valid.",
        )
        cls.url = reverse("feedback:feedback_save", args=[cls.page.pk])
        cls.detail = reverse("reports:page_detail", args=[cls.page.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url, {"sentiment": "POSITIVE"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertEqual(Feedback.objects.count(), 0)

    def test_only_post_is_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_first_submission_creates_feedback_and_updates_trust(self):
        response = self.client.post(self.url, {"sentiment": "NEGATIVE", "comment": " Never delivered. "}, follow=True)
        self.assertRedirects(response, self.detail)
        self.assertContains(response, "Thank you, your feedback was saved.")
        feedback = Feedback.objects.get()
        self.assertEqual((feedback.user, feedback.sentiment, feedback.comment), (self.user, "NEGATIVE", "Never delivered."))
        trust = TrustEvaluation.objects.get(page=self.page)
        self.assertEqual((trust.negative_count, trust.positive_count), (1, 0))

    def test_second_submission_edits_instead_of_duplicating(self):
        self.client.post(self.url, {"sentiment": "NEGATIVE", "comment": "Bad."})
        response = self.client.post(self.url, {"sentiment": "POSITIVE", "comment": "Sorted out, thanks."}, follow=True)
        self.assertContains(response, "Your feedback was updated.")
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertEqual(Feedback.objects.get().sentiment, "POSITIVE")
        trust = TrustEvaluation.objects.get(page=self.page)
        self.assertEqual((trust.positive_count, trust.negative_count), (1, 0))

    def test_editing_does_not_unhide_moderated_feedback(self):
        Feedback.objects.create(page=self.page, user=self.user, sentiment="NEGATIVE", is_hidden=True)
        self.client.post(self.url, {"sentiment": "POSITIVE", "comment": "Edited"})
        self.assertTrue(Feedback.objects.get().is_hidden)
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).positive_count, 0)

    def test_invalid_input_saves_nothing_and_shows_error(self):
        for data in ({}, {"sentiment": "MAYBE"}, {"sentiment": "POSITIVE", "comment": "x" * 1001}):
            with self.subTest(data=str(data)[:30]):
                response = self.client.post(self.url, data, follow=True)
                self.assertRedirects(response, self.detail)
                self.assertContains(response, "alert-danger")
        self.assertEqual(Feedback.objects.count(), 0)

    def test_page_without_public_info_is_404_except_for_admin(self):
        quiet = FacebookPage.objects.create(name="Quiet Shop", url="facebook.com/quiet.shop")
        url = reverse("feedback:feedback_save", args=[quiet.pk])
        self.assertEqual(self.client.post(url, {"sentiment": "POSITIVE"}).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(url, {"sentiment": "POSITIVE"}).status_code, 302)

    def test_post_without_csrf_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {"sentiment": "POSITIVE"}).status_code, 403)
        self.assertEqual(Feedback.objects.count(), 0)


class FeedbackFormOnPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        ScamReport.objects.create(
            page=cls.page, reporter=cls.user, category="OTHER", status=ScamReport.Status.APPROVED,
            title="A report title here", description="A description that is long enough to be valid.",
        )
        cls.detail = reverse("reports:page_detail", args=[cls.page.pk])

    def test_visitor_sees_login_prompt_not_form(self):
        response = self.client.get(self.detail)
        self.assertContains(response, "to share your experience with this page")
        self.assertNotContains(response, "Submit feedback")

    def test_logged_in_user_sees_empty_form_then_prefilled_form(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.detail), "Submit feedback")
        Feedback.objects.create(page=self.page, user=self.user, sentiment="NEGATIVE", comment="Blocked me.")
        response = self.client.get(self.detail)
        self.assertContains(response, "Update feedback")
        self.assertContains(response, "Blocked me.")
        html = response.content.decode()
        self.assertRegex(html, r'<input[^>]*value="NEGATIVE"[^>]*\bchecked\b')
        self.assertNotRegex(html, r'<input[^>]*value="POSITIVE"[^>]*\bchecked\b')

    def test_hidden_feedback_owner_is_told_it_is_hidden(self):
        self.client.force_login(self.user)
        Feedback.objects.create(page=self.page, user=self.user, sentiment="NEGATIVE", is_hidden=True)
        self.assertContains(self.client.get(self.detail), "A moderator has hidden your feedback")


class FeedbackDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner", "owner@example.com", "x")
        cls.other = User.objects.create_user("other", "other@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        ScamReport.objects.create(
            page=cls.page, reporter=cls.owner, category="OTHER", status=ScamReport.Status.APPROVED,
            title="A report title here", description="A description that is long enough to be valid.",
        )
        cls.detail = reverse("reports:page_detail", args=[cls.page.pk])

    def setUp(self):
        self.feedback = Feedback.objects.create(page=self.page, user=self.owner, sentiment="NEGATIVE", comment="Bad")
        self.url = reverse("feedback:feedback_delete", args=[self.feedback.pk])

    def test_owner_deletes_feedback_and_score_is_recalculated(self):
        from trustscore.services import recalculate_trust

        recalculate_trust(self.page)
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).negative_count, 1)
        self.client.force_login(self.owner)
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, self.detail)
        self.assertContains(response, "Your feedback was deleted.")
        self.assertEqual(Feedback.objects.count(), 0)
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).negative_count, 0)

    def test_owner_can_delete_even_if_moderator_hid_it(self):
        Feedback.objects.filter(pk=self.feedback.pk).update(is_hidden=True)
        self.client.force_login(self.owner)
        self.client.post(self.url)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_other_users_get_404_and_nothing_is_deleted(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_requires_login_and_post(self):
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_delete_button_only_for_own_existing_feedback(self):
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.detail), "Delete my feedback")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(self.detail), "Delete my feedback")
