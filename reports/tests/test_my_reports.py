from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from reports.models import Evidence, FacebookPage, ScamReport

from .helpers import TempMediaMixin, png_upload

User = get_user_model()
URL = reverse("reports:my_reports")


def make_report(reporter, page, title, **extra):
    return ScamReport.objects.create(
        page=page, reporter=reporter, category=ScamReport.Category.NON_DELIVERY, title=title,
        description="Paid in advance and the parcel never arrived at my address.", **extra,
    )


class MyReportsTests(TempMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("reporter", "reporter@example.com", "x")
        cls.other = User.objects.create_user("other", "other@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def setUp(self):
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(URL), f"{reverse('accounts:login')}?next={URL}")

    def test_lists_only_own_reports_newest_first(self):
        older = make_report(self.user, self.page, "My first report title")
        newer = make_report(self.user, self.page, "My second report title")
        make_report(self.other, self.page, "Someone else's report title")
        response = self.client.get(URL)
        self.assertEqual(list(response.context["page_obj"].object_list), [newer, older])
        self.assertNotContains(response, "Someone else")

    def test_shows_status_label_admin_note_and_evidence_count(self):
        report = make_report(self.user, self.page, "Needs more proof here", status=ScamReport.Status.NEEDS_EVIDENCE,
                             admin_note="Please add the payment receipt.")
        Evidence.objects.create(report=report, file=png_upload())
        response = self.client.get(URL)
        self.assertContains(response, "Needs more evidence")
        self.assertContains(response, "Please add the payment receipt.")
        self.assertContains(response, "1 file")

    def test_empty_state(self):
        self.assertContains(self.client.get(URL), "You haven't submitted any reports yet.")

    def test_paginates_ten_per_page(self):
        for i in range(12):
            make_report(self.user, self.page, f"Report number {i:02d} title")
        first = self.client.get(URL)
        self.assertEqual(len(first.context["page_obj"].object_list), 10)
        self.assertContains(first, "Page 1 of 2")
        second = self.client.get(URL, {"page": 2})
        self.assertEqual(len(second.context["page_obj"].object_list), 2)

    def test_query_count_does_not_grow_with_number_of_reports(self):
        make_report(self.user, self.page, "Only one report title")
        with CaptureQueriesContext(connection) as one_report:
            self.client.get(URL)
        for i in range(8):
            make_report(self.user, self.page, f"Another report {i} title")
        with self.assertNumQueries(len(one_report.captured_queries)):
            self.client.get(URL)


class ProfileRecentReportsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("reporter", "reporter@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def setUp(self):
        self.client.force_login(self.user)

    def test_profile_shows_latest_five_and_link_to_all(self):
        for i in range(7):
            make_report(self.user, self.page, f"Profile report {i} title")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(len(response.context["recent_reports"]), 5)
        self.assertContains(response, f'href="{URL}"')
        self.assertContains(response, "View all 7")

    def test_profile_without_reports_invites_to_report(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, f'href="{reverse("reports:report_create")}"')
