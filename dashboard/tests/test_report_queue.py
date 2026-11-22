from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.services import report_queue
from reports.models import FacebookPage, ScamReport

User = get_user_model()
S = ScamReport.Status
URL = reverse("dashboard:report_queue")


class ReportQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        now = timezone.now()
        cls.reports = {}
        for key, status, days_ago in [("old_pending", S.PENDING, 10), ("new_pending", S.PENDING, 1),
                                      ("evidence", S.NEEDS_EVIDENCE, 5), ("approved", S.APPROVED, 8),
                                      ("rejected", S.REJECTED, 3)]:
            report = ScamReport.objects.create(page=cls.page, reporter=cls.user, category="OTHER", status=status,
                                               title=f"Title {key} report", description="A description that is long enough.")
            ScamReport.objects.filter(pk=report.pk).update(created_at=now - timedelta(days=days_ago))
            cls.reports[key] = report.pk

    def setUp(self):
        self.client.force_login(self.admin)

    def ids(self, tab):
        queryset, _, _ = report_queue(tab)
        return [r.pk for r in queryset]

    def test_default_tab_is_under_review_oldest_first(self):
        self.assertEqual(self.ids(""), [self.reports["old_pending"], self.reports["new_pending"]])
        self.assertEqual(self.ids("garbage"), self.ids("PENDING"))

    def test_other_tabs_filter_by_status_newest_first(self):
        self.assertEqual(self.ids("NEEDS_EVIDENCE"), [self.reports["evidence"]])
        self.assertEqual(self.ids("APPROVED"), [self.reports["approved"]])
        self.assertEqual(self.ids("REJECTED"), [self.reports["rejected"]])
        self.assertEqual(self.ids("ALL"), [self.reports[k] for k in ("new_pending", "rejected", "evidence", "approved", "old_pending")])

    def test_tab_counts(self):
        _, tabs, active = report_queue("")
        self.assertEqual({value: count for value, _, count in tabs},
                         {"PENDING": 2, "NEEDS_EVIDENCE": 1, "APPROVED": 1, "REJECTED": 1, "ALL": 5})
        self.assertEqual(active, "PENDING")

    def test_page_shows_rows_and_active_tab(self):
        response = self.client.get(URL, {"status": "APPROVED"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Title approved report")
        self.assertNotContains(response, "Title old_pending report")
        self.assertContains(response, 'aria-current="page"')

    def test_empty_tab_message(self):
        ScamReport.objects.filter(status=S.REJECTED).delete()
        self.assertContains(self.client.get(URL, {"status": "REJECTED"}), "No reports in this tab.")

    def test_pagination_keeps_status_tab(self):
        for i in range(16):
            ScamReport.objects.create(page=self.page, reporter=self.user, category="OTHER", status=S.PENDING,
                                      title=f"Bulk report number {i}", description="A description that is long enough.")
        response = self.client.get(URL)
        self.assertEqual(len(response.context["page_obj"].object_list), 15)
        self.assertContains(response, "?status=PENDING&amp;page=2")

    def test_access_control(self):
        self.client.logout()
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_sidebar_and_overview_link_to_queue(self):
        self.assertContains(self.client.get(reverse("dashboard:overview")), f'href="{URL}"')
