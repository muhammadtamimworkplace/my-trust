from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from feedback.models import Comment, Feedback, FeedbackVote
from reports.models import FacebookPage, ScamReport

User = get_user_model()


class CommunityModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", "alice@example.com", "x")
        cls.bob = User.objects.create_user("bob", "bob@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.other_page = FacebookPage.objects.create(name="Other Shop", url="facebook.com/other.shop")
        cls.report = ScamReport.objects.create(
            page=cls.page, reporter=cls.alice, category=ScamReport.Category.NON_DELIVERY,
            title="Order never arrived", description="Paid for shoes three weeks ago, nothing delivered.",
        )

    def test_one_feedback_per_user_per_page(self):
        Feedback.objects.create(page=self.page, user=self.alice, sentiment=Feedback.Sentiment.NEGATIVE)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Feedback.objects.create(page=self.page, user=self.alice, sentiment=Feedback.Sentiment.POSITIVE)

    def test_same_user_may_give_feedback_on_different_pages(self):
        Feedback.objects.create(page=self.page, user=self.alice, sentiment="NEGATIVE")
        Feedback.objects.create(page=self.other_page, user=self.alice, sentiment="POSITIVE")
        self.assertEqual(self.alice.feedback_given.count(), 2)

    def test_feedback_defaults_and_validation(self):
        feedback = Feedback(page=self.page, user=self.bob, sentiment="POSITIVE", comment="x" * 1001)
        self.assertFalse(feedback.is_hidden)
        with self.assertRaises(ValidationError) as ctx:
            feedback.full_clean()
        self.assertIn("comment", ctx.exception.message_dict)
        with self.assertRaises(ValidationError):
            Feedback(page=self.page, user=self.bob, sentiment="MAYBE").full_clean()

    def test_one_vote_per_user_per_feedback(self):
        feedback = Feedback.objects.create(page=self.page, user=self.alice, sentiment="NEGATIVE")
        FeedbackVote.objects.create(feedback=feedback, user=self.bob, value=FeedbackVote.Value.LIKE)
        with self.assertRaises(IntegrityError), transaction.atomic():
            FeedbackVote.objects.create(feedback=feedback, user=self.bob, value=FeedbackVote.Value.DISLIKE)

    def test_database_rejects_vote_values_other_than_plus_or_minus_one(self):
        feedback = Feedback.objects.create(page=self.page, user=self.alice, sentiment="NEGATIVE")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FeedbackVote.objects.create(feedback=feedback, user=self.bob, value=5)

    def test_comment_length_rules(self):
        for body in ("x", "y" * 1001):
            with self.subTest(length=len(body)), self.assertRaises(ValidationError):
                Comment(report=self.report, user=self.bob, body=body).full_clean()
        Comment(report=self.report, user=self.bob, body="Same happened to me.").full_clean()

    def test_deleting_a_report_removes_its_comments(self):
        Comment.objects.create(report=self.report, user=self.bob, body="Same here.")
        self.report.delete()
        self.assertEqual(Comment.objects.count(), 0)

    def test_string_representations(self):
        feedback = Feedback.objects.create(page=self.page, user=self.alice, sentiment="NEGATIVE")
        vote = FeedbackVote.objects.create(feedback=feedback, user=self.bob, value=1)
        self.assertEqual(str(feedback), "Negative feedback on Example Shop by alice")
        self.assertEqual(str(vote), f"Like by bob on feedback #{feedback.pk}")
