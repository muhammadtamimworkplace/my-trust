import io

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from feedback.models import Feedback
from reports.models import FacebookPage, ScamReport
from reports.services import submit_report
from reports.tests.helpers import TempMediaMixin, png_upload
from trustscore.models import TrustEvaluation
from trustscore.services import calculate_score, recalculate_trust

User = get_user_model()
S = ScamReport.Status
L = TrustEvaluation.Label


class RecalculateTrustTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [User.objects.create_user(f"user{i}", f"user{i}@example.com", "x") for i in range(10)]
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def report(self, status, reporter=None):
        return ScamReport.objects.create(
            page=self.page, reporter=reporter or self.users[0], category="OTHER", status=status,
            title="A report title here", description="A description that is long enough to be valid.",
        )

    def feedback(self, user, sentiment, hidden=False):
        return Feedback.objects.create(page=self.page, user=user, sentiment=sentiment, is_hidden=hidden)

    def test_snapshot_matches_formula_and_counts(self):
        for user in self.users[:8]:
            self.feedback(user, "POSITIVE")
        for user in self.users[8:10]:
            self.feedback(user, "NEGATIVE")
        self.report(S.APPROVED)
        trust = recalculate_trust(self.page)
        self.assertEqual((trust.score, trust.label), calculate_score(8, 2, 1))
        self.assertEqual((trust.positive_count, trust.negative_count, trust.verified_report_count), (8, 2, 1))

    def test_unverified_reports_change_only_pending_count_never_score(self):
        for user in self.users[:3]:
            self.feedback(user, "POSITIVE")
        before = recalculate_trust(self.page)
        self.report(S.PENDING)
        self.report(S.NEEDS_EVIDENCE)
        self.report(S.REJECTED)
        after = recalculate_trust(self.page)
        self.assertEqual((after.score, after.label), (before.score, before.label))
        self.assertEqual(after.pending_report_count, 2)
        self.assertEqual(after.verified_report_count, 0)

    def test_hidden_feedback_is_excluded(self):
        for user in self.users[:3]:
            self.feedback(user, "NEGATIVE", hidden=True)
        trust = recalculate_trust(self.page)
        self.assertEqual((trust.negative_count, trust.label), (0, L.INSUFFICIENT))

    def test_recalculating_updates_the_same_row(self):
        recalculate_trust(self.page)
        self.report(S.APPROVED)
        recalculate_trust(self.page)
        self.assertEqual(TrustEvaluation.objects.count(), 1)
        # Read from the DB: page.trust may hold the instance cached when it was first created.
        self.assertEqual(TrustEvaluation.objects.get(page=self.page).verified_report_count, 1)

    def test_uses_a_fixed_number_of_queries(self):
        for user in self.users:
            self.feedback(user, "POSITIVE")
        for _ in range(5):
            self.report(S.APPROVED)
        TrustEvaluation.objects.create(page=self.page)
        # 2 aggregate counts + update_or_create (select-for-update + update) inside a savepoint
        with self.assertNumQueries(6):
            recalculate_trust(self.page)

    def test_report_submission_creates_snapshot(self):
        report = submit_report(
            reporter=self.users[0], page_name="New Shop", page_url="https://www.facebook.com/new.shop",
            report_data={"category": "OTHER", "title": "A report title here",
                         "description": "A description that is long enough to be valid."},
            evidence_files=[png_upload()],
        )
        trust = report.page.trust
        self.assertEqual((trust.pending_report_count, trust.score, trust.label), (1, 50, L.INSUFFICIENT))


class RecalculateCommandTests(TestCase):
    def test_command_rebuilds_every_page(self):
        pages = [FacebookPage.objects.create(name=f"Shop {i}", url=f"facebook.com/shop{i}") for i in range(3)]
        TrustEvaluation.objects.create(page=pages[0], score=99, label=L.GOOD)  # stale / tampered value
        out = io.StringIO()
        call_command("recalculate_trust", stdout=out)
        self.assertIn("3 page(s)", out.getvalue())
        self.assertEqual(TrustEvaluation.objects.count(), 3)
        self.assertEqual(TrustEvaluation.objects.get(page=pages[0]).score, 50)
