from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from feedback.models import Feedback, FeedbackVote
from feedback.services import vote_on_feedback
from reports.models import FacebookPage, ScamReport
from trustscore.models import TrustEvaluation
from trustscore.services import recalculate_trust

User = get_user_model()
LIKE, DISLIKE = FeedbackVote.Value.LIKE, FeedbackVote.Value.DISLIKE


class VoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user("author", "author@example.com", "x")
        cls.voter = User.objects.create_user("voter", "voter@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        ScamReport.objects.create(
            page=cls.page, reporter=cls.author, category="OTHER", status=ScamReport.Status.APPROVED,
            title="A report title here", description="A description that is long enough to be valid.",
        )
        cls.detail = reverse("reports:page_detail", args=[cls.page.pk])

    def setUp(self):
        self.feedback = Feedback.objects.create(page=self.page, user=self.author, sentiment="NEGATIVE", comment="Bad")
        self.url = reverse("feedback:feedback_vote", args=[self.feedback.pk])

    # ---- service ----
    def test_toggle_logic(self):
        self.assertEqual(vote_on_feedback(user=self.voter, feedback=self.feedback, value=LIKE), LIKE)
        self.assertEqual(vote_on_feedback(user=self.voter, feedback=self.feedback, value=DISLIKE), DISLIKE)  # switch
        self.assertEqual(FeedbackVote.objects.count(), 1)
        self.assertIsNone(vote_on_feedback(user=self.voter, feedback=self.feedback, value=DISLIKE))  # remove
        self.assertEqual(FeedbackVote.objects.count(), 0)

    def test_cannot_vote_on_own_or_hidden_feedback_or_with_bad_value(self):
        with self.assertRaises(ValidationError):
            vote_on_feedback(user=self.author, feedback=self.feedback, value=LIKE)
        with self.assertRaises(ValidationError):
            vote_on_feedback(user=self.voter, feedback=self.feedback, value=7)
        self.feedback.is_hidden = True
        with self.assertRaises(ValidationError):
            vote_on_feedback(user=self.voter, feedback=self.feedback, value=LIKE)
        self.assertEqual(FeedbackVote.objects.count(), 0)

    def test_votes_never_change_the_trust_score(self):
        before = recalculate_trust(self.page).score
        vote_on_feedback(user=self.voter, feedback=self.feedback, value=LIKE)
        self.assertEqual(recalculate_trust(self.page).score, before)
        self.assertEqual(TrustEvaluation.objects.count(), 1)

    # ---- view ----
    def test_view_requires_login_and_post(self):
        self.assertEqual(self.client.post(self.url, {"value": "like"}).status_code, 302)
        self.client.force_login(self.voter)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(FeedbackVote.objects.count(), 0)

    def test_like_dislike_and_remove_through_the_view(self):
        self.client.force_login(self.voter)
        self.client.post(self.url, {"value": "like"})
        self.assertEqual(FeedbackVote.objects.get().value, 1)
        self.client.post(self.url, {"value": "dislike"})
        self.assertEqual(FeedbackVote.objects.get().value, -1)
        self.client.post(self.url, {"value": "dislike"})
        self.assertEqual(FeedbackVote.objects.count(), 0)

    def test_own_feedback_and_bad_values_show_an_error(self):
        self.client.force_login(self.author)
        response = self.client.post(self.url, {"value": "like"}, follow=True)
        self.assertContains(response, "You cannot vote on your own feedback.")
        self.client.force_login(self.voter)
        self.assertContains(self.client.post(self.url, {"value": "banana"}, follow=True), "Invalid vote.")
        self.assertEqual(FeedbackVote.objects.count(), 0)

    def test_hidden_feedback_is_404(self):
        Feedback.objects.filter(pk=self.feedback.pk).update(is_hidden=True)
        self.client.force_login(self.voter)
        self.assertEqual(self.client.post(self.url, {"value": "like"}).status_code, 404)

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.voter)
        self.assertEqual(client.post(self.url, {"value": "like"}).status_code, 403)

    # ---- page display ----
    def test_page_shows_counts_and_the_viewers_own_vote(self):
        other = User.objects.create_user("other", "other@example.com", "x")
        FeedbackVote.objects.create(feedback=self.feedback, user=other, value=LIKE)
        FeedbackVote.objects.create(feedback=self.feedback, user=self.voter, value=DISLIKE)
        self.client.force_login(self.voter)
        response = self.client.get(self.detail)
        item = response.context["feedback"][0]
        self.assertEqual((item.likes, item.dislikes, item.my_vote), (1, 1, -1))
        self.assertContains(response, 'aria-label="Not helpful"')

    def test_author_and_visitors_see_counts_without_buttons(self):
        for user in (None, self.author):
            with self.subTest(user=getattr(user, "username", "visitor")):
                self.client.logout()
                if user:
                    self.client.force_login(user)
                response = self.client.get(self.detail)
                self.assertNotContains(response, 'aria-label="Helpful"')
                self.assertContains(response, "👍")
