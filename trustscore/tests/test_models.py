from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from reports.models import FacebookPage
from trustscore.models import TrustEvaluation


class TrustEvaluationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def test_defaults_are_neutral_with_no_data(self):
        trust = TrustEvaluation.objects.create(page=self.page)
        self.assertEqual((trust.score, trust.label), (50, TrustEvaluation.Label.INSUFFICIENT))
        self.assertEqual(trust.get_label_display(), "Not enough data")
        self.assertEqual(self.page.trust, trust)

    def test_one_evaluation_per_page(self):
        TrustEvaluation.objects.create(page=self.page)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TrustEvaluation.objects.create(page=self.page)

    def test_score_above_100_is_rejected_by_validation_and_database(self):
        with self.assertRaises(ValidationError):
            TrustEvaluation(page=self.page, score=101).full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            TrustEvaluation.objects.create(page=self.page, score=101)

    def test_no_label_mentions_fraud_or_scam(self):
        for label in TrustEvaluation.Label.labels:
            self.assertNotRegex(label.lower(), r"fraud|scam")

    def test_str(self):
        trust = TrustEvaluation.objects.create(page=self.page, score=72, label=TrustEvaluation.Label.GOOD)
        self.assertEqual(str(trust), "Example Shop: 72 (Good reputation)")
