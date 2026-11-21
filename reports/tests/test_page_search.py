from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from feedback.models import Feedback
from reports.models import FacebookPage, ScamReport
from reports.services import search_pages
from trustscore.services import recalculate_trust

User = get_user_model()
S = ScamReport.Status
C = ScamReport.Category
URL = reverse("reports:page_list")


class PageSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("reporter", "reporter@example.com", "x")
        cls.closet = cls.page("Trendy Closet", "trendy.closet", (C.ADVANCE_PAYMENT, S.APPROVED))
        cls.gadget = cls.page("Gadget Bazaar", "gadget.bazaar", (C.FAKE_PRODUCT, S.PENDING))
        cls.shoes = cls.page("Shoe Planet", "shoe.planet", (C.FAKE_PRODUCT, S.APPROVED), (C.NON_DELIVERY, S.NEEDS_EVIDENCE))
        cls.rejected_only = cls.page("Kids Corner", "kids.corner", (C.FAKE_PRODUCT, S.REJECTED))
        cls.feedback_only = cls.page("Organic Basket", "organic.basket")
        Feedback.objects.create(page=cls.feedback_only, user=cls.user, sentiment="POSITIVE")
        for page in FacebookPage.objects.all():
            recalculate_trust(page)

    @classmethod
    def page(cls, name, slug, *reports):
        page = FacebookPage.objects.create(name=name, url=f"facebook.com/{slug}")
        for category, status in reports:
            ScamReport.objects.create(
                page=page, reporter=cls.user, category=category, status=status,
                title="A report title here", description="A description that is long enough to be valid.",
            )
        return page

    def names(self, **filters):
        return sorted(p.name for p in search_pages(**filters))

    def test_lists_only_pages_with_public_information(self):
        self.assertEqual(self.names(), ["Gadget Bazaar", "Organic Basket", "Shoe Planet", "Trendy Closet"])
        self.assertNotIn("Kids Corner", self.names())

    def test_name_search_is_partial_and_case_insensitive(self):
        self.assertEqual(self.names(query="closet"), ["Trendy Closet"])
        self.assertEqual(self.names(query="  BAZAAR "), ["Gadget Bazaar"])

    def test_link_search_matches_any_form_of_the_url(self):
        for link in ("https://m.facebook.com/Trendy.Closet/?ref=share", "fb.com/trendy.closet", "facebook.com/trendy.closet/"):
            with self.subTest(link=link):
                self.assertEqual(self.names(query=link), ["Trendy Closet"])

    def test_link_search_does_not_partially_match_other_pages(self):
        self.assertEqual(self.names(query="facebook.com/trendy"), [])

    def test_category_filter_ignores_rejected_reports(self):
        self.assertEqual(self.names(category=C.FAKE_PRODUCT), ["Gadget Bazaar", "Shoe Planet"])
        self.assertEqual(self.names(category=C.NON_DELIVERY), ["Shoe Planet"])

    def test_verification_filters(self):
        self.assertEqual(self.names(verification="verified"), ["Shoe Planet", "Trendy Closet"])
        self.assertEqual(self.names(verification="unverified"), ["Gadget Bazaar"])

    def test_filters_combine(self):
        self.assertEqual(self.names(category=C.FAKE_PRODUCT, verification="verified"), ["Shoe Planet"])

    def test_view_renders_results_with_compact_badges(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/page_list.html")
        self.assertContains(response, "4 pages found")
        self.assertContains(response, "mt-trust-pill")
        self.assertNotContains(response, "Kids Corner")

    def test_view_applies_query_parameters(self):
        response = self.client.get(URL, {"q": "m.facebook.com/shoe.planet", "status": "verified"})
        self.assertContains(response, "1 page found for your filters")
        self.assertContains(response, "Shoe Planet")
        self.assertContains(response, "Clear filters")

    def test_invalid_filter_values_are_ignored_safely(self):
        response = self.client.get(URL, {"category": "DROP TABLE", "status": "<script>"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4 pages found")
        self.assertNotContains(response, "<script>")

    def test_empty_result_warns_that_no_reports_does_not_mean_safe(self):
        response = self.client.get(URL, {"q": "no such shop"})
        self.assertContains(response, "No reports doesn")

    def test_pagination_keeps_filters(self):
        for i in range(13):
            self.page(f"Bulk Shop {i:02d}", f"bulk.shop{i}", (C.OTHER, S.PENDING))
        response = self.client.get(URL, {"q": "bulk"})
        self.assertEqual(len(response.context["page_obj"].object_list), 12)
        self.assertContains(response, "?q=bulk&amp;page=2")

    def test_navbar_browse_link_is_active(self):
        response = self.client.get(URL)
        self.assertContains(response, f'href="{URL}">Browse pages')
        self.assertContains(response, 'aria-current="page"')


class SearchEntryPointTests(TestCase):
    def test_landing_search_submits_to_page_list(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, f'action="{URL}" method="get" role="search"')
        self.assertNotContains(response, 'id="nav-search"')  # hero already has a big search box

    def test_navbar_search_appears_on_other_pages(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, 'id="nav-search"')
        self.assertContains(response, f'action="{URL}"')

    def test_navbar_search_hidden_on_results_page_which_has_its_own_form(self):
        self.assertNotContains(self.client.get(URL), 'id="nav-search"')

    def test_search_from_landing_page_reaches_results(self):
        page = FacebookPage.objects.create(name="Gadget Bazaar", url="facebook.com/gadget.bazaar")
        reporter = User.objects.create_user("r", "r@example.com", "x")
        ScamReport.objects.create(page=page, reporter=reporter, category=C.OTHER, status=S.PENDING,
                                  title="A report title here", description="A description that is long enough to be valid.")
        response = self.client.get(URL, {"q": "gadget"})
        self.assertContains(response, "Gadget Bazaar")
