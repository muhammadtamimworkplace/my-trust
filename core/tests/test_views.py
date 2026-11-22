from django.test import TestCase
from django.urls import resolve, reverse

from core import views


class HomePageTests(TestCase):
    """Landing page (P2-T07). TestCase since P8-T05: the page now reads recent community activity."""

    def setUp(self):
        self.response = self.client.get(reverse("core:home"))

    def test_root_url_resolves_to_home_view(self):
        self.assertEqual(reverse("core:home"), "/")
        self.assertIs(resolve("/").func, views.home)

    def test_returns_200_with_home_template(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, "base.html")
        self.assertTemplateUsed(self.response, "core/home.html")

    def test_search_form_submits_query_to_pages_list(self):
        self.assertContains(self.response, '<form class="mt-search mx-auto" action="/pages/" method="get"')
        self.assertContains(self.response, 'name="q"')

    def test_all_scam_categories_are_listed(self):
        for category in views.SCAM_CATEGORIES:
            self.assertContains(self.response, category["title"])

    def test_explains_verified_unverified_and_community_labels(self):
        for label in ("Verified by admin", "Unverified allegation", "Community feedback"):
            self.assertContains(self.response, label)

    def test_home_nav_link_is_marked_current(self):
        self.assertContains(self.response, 'aria-current="page"')


class RecentActivityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        from feedback.models import Feedback
        from reports.models import FacebookPage, ScamReport

        user = get_user_model().objects.create_user("buyer", "buyer-private@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        for title, status in (("Verified report headline", "APPROVED"), ("Pending report headline", "PENDING"),
                              ("Rejected report headline", "REJECTED")):
            ScamReport.objects.create(page=cls.page, reporter=user, category="OTHER", status=status, title=title,
                                      description="A description that is long enough to be valid.")
        Feedback.objects.create(page=cls.page, user=user, sentiment="NEGATIVE", comment="Hidden words", is_hidden=True)
        cls.user = user
        cls.Feedback = Feedback

    def test_section_is_hidden_when_there_is_no_activity(self):
        self.page.reports.all().delete()
        self.page.feedback.all().delete()
        self.assertNotContains(self.client.get("/"), "Recent community activity")

    def test_only_verified_reports_are_listed(self):
        response = self.client.get("/")
        self.assertContains(response, "Verified report headline")
        self.assertNotContains(response, "Pending report headline")
        self.assertNotContains(response, "Rejected report headline")

    def test_hidden_feedback_is_not_shown_but_visible_feedback_is(self):
        self.assertNotContains(self.client.get("/"), "Latest community feedback")
        other = type(self.user).objects.create_user("fan", "fan@example.com", "x")
        self.Feedback.objects.create(page=self.page, user=other, sentiment="POSITIVE")
        response = self.client.get("/")
        self.assertContains(response, "Latest community feedback")
        self.assertContains(response, "fan")
        self.assertNotContains(response, "buyer-private@example.com")

    def test_limits_are_respected(self):
        from reports.models import ScamReport

        for i in range(5):
            ScamReport.objects.create(page=self.page, reporter=self.user, category="OTHER", status="APPROVED",
                                      title=f"Extra verified {i}", description="A description that is long enough.")
        self.assertEqual(len(self.client.get("/").context["recent_verified_reports"]), 3)
