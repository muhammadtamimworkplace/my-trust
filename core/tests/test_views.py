from django.test import SimpleTestCase
from django.urls import resolve, reverse

from core import views


class HomePageTests(SimpleTestCase):
    """Landing page (P2-T07). SimpleTestCase also proves the page needs no database queries."""

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
