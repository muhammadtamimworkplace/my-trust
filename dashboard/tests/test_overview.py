from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from dashboard.services import overview_stats, with_percent
from feedback.models import Comment, Feedback
from reports.models import FacebookPage, ScamReport

User = get_user_model()
S = ScamReport.Status
C = ScamReport.Category
URL = reverse("dashboard:overview")


class OverviewAccessTests(TestCase):
    def test_visitor_is_redirected_to_login(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_regular_user_is_forbidden(self):
        self.client.force_login(User.objects.create_user("member", "member@example.com", "x"))
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_admin_and_superuser_can_open_it(self):
        for user in (User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN),
                     User.objects.create_superuser("root", "root@example.com", "x")):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(URL)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "dashboard/overview.html")

    def test_navbar_dashboard_link_is_real_for_admins_only(self):
        self.client.force_login(User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN))
        self.assertContains(self.client.get("/"), f'href="{URL}"')
        self.client.force_login(User.objects.create_user("member", "member@example.com", "x"))
        self.assertNotContains(self.client.get("/"), f'href="{URL}"')


class OverviewStatsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "x")
        cls.a = FacebookPage.objects.create(name="Alpha Shop", url="facebook.com/alpha")
        cls.b = FacebookPage.objects.create(name="Beta Shop", url="facebook.com/beta")
        for page, category, status in [
            (cls.a, C.ADVANCE_PAYMENT, S.APPROVED), (cls.a, C.ADVANCE_PAYMENT, S.PENDING),
            (cls.a, C.FAKE_PRODUCT, S.REJECTED), (cls.b, C.FAKE_PRODUCT, S.APPROVED),
            (cls.b, C.NON_DELIVERY, S.NEEDS_EVIDENCE),
        ]:
            ScamReport.objects.create(page=page, reporter=cls.user, category=category, status=status,
                                      title="A report title here", description="A description that is long enough.")
        Feedback.objects.create(page=cls.a, user=cls.user, sentiment="NEGATIVE")
        Comment.objects.create(report=ScamReport.objects.first(), user=cls.user, body="A comment")

    def test_totals(self):
        self.assertEqual(overview_stats()["totals"], {"users": 2, "pages": 2, "reports": 5, "feedback": 1, "comments": 1})

    def test_reports_by_status_includes_every_status(self):
        rows = {row["status"]: row["total"] for row in overview_stats()["status_rows"]}
        self.assertEqual(rows, {S.PENDING: 1, S.NEEDS_EVIDENCE: 1, S.APPROVED: 2, S.REJECTED: 1})

    def test_reports_by_category_counts_total_and_verified_and_includes_empty_categories(self):
        rows = {row["category"]: (row["total"], row["verified"]) for row in overview_stats()["category_rows"]}
        self.assertEqual(rows[C.ADVANCE_PAYMENT], (2, 1))
        self.assertEqual(rows[C.FAKE_PRODUCT], (2, 1))
        self.assertEqual(rows[C.NON_DELIVERY], (1, 0))
        self.assertEqual(rows[C.HARASSMENT], (0, 0))
        self.assertEqual(len(rows), len(C.choices))

    def test_most_reported_pages_ignore_rejected_reports(self):
        top = list(overview_stats()["top_pages"])
        self.assertEqual([(p.name, p.public_reports, p.verified_reports) for p in top],
                         [("Alpha Shop", 2, 1), ("Beta Shop", 2, 1)])

    def test_awaiting_review_counts_only_pending(self):
        self.assertEqual(overview_stats()["awaiting_review"], 1)

    def test_percentages_and_empty_database(self):
        self.assertEqual([r["percent"] for r in with_percent([{"total": 1}, {"total": 3}], 4)], [25, 75])
        self.assertEqual(with_percent([{"total": 0}], 0)[0]["percent"], 0)

    def test_page_renders_numbers_progress_bars_and_no_inline_styles(self):
        self.client.force_login(self.admin)
        response = self.client.get(URL)
        self.assertContains(response, "Reports by scam category")
        self.assertContains(response, "Advance payment")
        self.assertContains(response, "<progress")
        self.assertContains(response, "1</strong> report waiting for review")
        self.assertNotContains(response, 'style="')

    def test_query_count_does_not_grow_with_data(self):
        self.client.force_login(self.admin)
        with CaptureQueriesContext(connection) as before:
            self.client.get(URL)
        for i in range(6):
            page = FacebookPage.objects.create(name=f"Extra {i}", url=f"facebook.com/extra{i}")
            ScamReport.objects.create(page=page, reporter=self.user, category=C.OTHER, status=S.PENDING,
                                      title="A report title here", description="A description that is long enough.")
        with self.assertNumQueries(len(before.captured_queries)):
            self.client.get(URL)
