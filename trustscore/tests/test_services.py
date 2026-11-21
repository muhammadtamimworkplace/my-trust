from django.test import SimpleTestCase

from trustscore.models import TrustEvaluation
from trustscore.services import calculate_score, round_half_up

L = TrustEvaluation.Label


class CalculateScoreTests(SimpleTestCase):
    def test_worked_example_from_guide(self):
        self.assertEqual(calculate_score(8, 2, 1), (60, L.MIXED))

    def test_no_data_is_neutral_and_insufficient(self):
        self.assertEqual(calculate_score(0, 0, 0), (50, L.INSUFFICIENT))

    def test_fewer_than_three_feedback_and_no_verified_report_is_insufficient(self):
        self.assertEqual(calculate_score(2, 0, 0)[1], L.INSUFFICIENT)
        self.assertEqual(calculate_score(0, 2, 0)[1], L.INSUFFICIENT)
        self.assertEqual(calculate_score(1, 1, 0)[1], L.INSUFFICIENT)

    def test_a_verified_report_always_produces_a_rating(self):
        self.assertEqual(calculate_score(0, 0, 1), (35, L.CAUTION))

    def test_label_boundaries(self):
        cases = [
            ((6, 2, 0), 70, L.GOOD),     # 7/10 = 70 exactly -> Good
            ((4, 1, 0), 71, L.GOOD),     # 5/7 = 71.4
            ((2, 1, 0), 60, L.MIXED),    # 3/5 = 60
            ((1, 2, 0), 40, L.MIXED),    # 2/5 = 40 exactly -> Mixed (not Caution)
            ((0, 3, 0), 20, L.CAUTION),  # 1/5 = 20
            ((3, 0, 0), 80, L.GOOD),
        ]
        for counts, score, label in cases:
            with self.subTest(counts=counts):
                self.assertEqual(calculate_score(*counts), (score, label))

    def test_each_verified_report_removes_fifteen_points_up_to_sixty(self):
        base = calculate_score(98, 0, 0)[0]  # 99/100 = 99
        self.assertEqual(base, 99)
        self.assertEqual([calculate_score(98, 0, v)[0] for v in range(6)], [99, 84, 69, 54, 39, 39])

    def test_score_never_goes_below_zero_or_above_100(self):
        self.assertEqual(calculate_score(0, 50, 10)[0], 0)
        self.assertEqual(calculate_score(10_000, 0, 0)[0], 100)

    def test_unverified_reports_are_not_an_input(self):
        # The function has no parameter for unverified reports, by design (guide §9 principle 1).
        self.assertEqual(calculate_score.__code__.co_argcount, 3)

    def test_rounding_is_half_up_not_bankers(self):
        self.assertEqual(round_half_up(12.5), 13)
        self.assertEqual(round_half_up(12.4999), 12)
        self.assertEqual(calculate_score(0, 6, 0)[0], 13)  # 1/8 = 12.5

    def test_negative_counts_are_rejected(self):
        for counts in ((-1, 0, 0), (0, -1, 0), (0, 0, -1)):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                calculate_score(*counts)
