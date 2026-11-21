from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from reports.models import FacebookPage, ScamReport
from trustscore.models import TrustEvaluation

L = TrustEvaluation.Label
DISCLAIMER = "Scores reflect community feedback and admin-verified reports only. Unverified reports are allegations."


def render(trust, compact=False):
    return render_to_string("partials/_trust_badge.html", {"trust": trust, "compact": compact})


class TrustBadgeTemplateTests(SimpleTestCase):
    def trust(self, score, label, **counts):
        return TrustEvaluation(score=score, label=label, **counts)

    def test_full_badge_shows_score_label_separate_counts_and_disclaimer(self):
        html = render(self.trust(60, L.MIXED, verified_report_count=1, pending_report_count=2,
                                 positive_count=8, negative_count=2))
        self.assertIn("mt-trust--mixed", html)
        self.assertIn('aria-label="Trust score 60 out of 100"', html)
        self.assertIn("Mixed reputation", html)
        for text in ("Verified reports", "Unverified allegations", "Community feedback", "👍 8", "👎 2"):
            self.assertIn(text, html)
        self.assertIn(DISCLAIMER, html)

    def test_each_label_gets_its_colour_class(self):
        for label in L.values:
            with self.subTest(label=label):
                self.assertIn(f"mt-trust--{label.lower()}", render(self.trust(50, label)))

    def test_insufficient_data_shows_no_number(self):
        html = render(self.trust(50, L.INSUFFICIENT))
        self.assertIn("Not enough data", html)
        self.assertNotIn(">50<", html.replace("\n", "").replace(" ", ""))
        self.assertIn('aria-label="No score yet"', html)

    def test_compact_pill_for_lists(self):
        html = render(self.trust(80, L.GOOD), compact=True)
        self.assertIn("mt-trust-pill", html)
        self.assertIn("<strong>80</strong>", html)
        self.assertNotIn(DISCLAIMER, html)
        self.assertNotIn("<strong>", render(self.trust(50, L.INSUFFICIENT), compact=True))

    def test_missing_evaluation_is_not_yet_rated(self):
        self.assertIn("Not yet rated", render(None))

    def test_no_wording_calls_a_page_fraudulent(self):
        for label in L.values:
            html = render(self.trust(0, label)).lower()
            self.assertNotIn("fraud", html)
            self.assertNotIn("scammer", html)


class ReportPageShowsBadgeTests(TestCase):
    def test_report_detail_sidebar_shows_page_trust_badge(self):
        user = get_user_model().objects.create_user("reporter", "reporter@example.com", "x")
        page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        TrustEvaluation.objects.create(page=page, score=35, label=L.CAUTION, verified_report_count=1)
        report = ScamReport.objects.create(
            page=page, reporter=user, category="OTHER", status=ScamReport.Status.APPROVED,
            title="A report title here", description="A description that is long enough to be valid.",
        )
        response = self.client.get(reverse("reports:report_detail", args=[report.pk]))
        self.assertContains(response, "Use caution")
        self.assertContains(response, DISCLAIMER)
