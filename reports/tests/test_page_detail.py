from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from feedback.models import Feedback
from reports.models import FacebookPage, ScamReport
from trustscore.services import recalculate_trust

User = get_user_model()
S = ScamReport.Status


class PageDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reporter = User.objects.create_user("reporter", "reporter-private@example.com", "x")
        cls.fan = User.objects.create_user("fan", "fan@example.com", "x")
        cls.critic = User.objects.create_user("critic", "critic@example.com", "x")
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.page = FacebookPage.objects.create(name="Trendy Closet", url="facebook.com/trendy.closet")
        for title, status in (("Verified advance payment scam", S.APPROVED), ("Pending non delivery claim", S.PENDING),
                              ("Needs evidence fake product", S.NEEDS_EVIDENCE), ("Rejected minor delay issue", S.REJECTED)):
            ScamReport.objects.create(page=cls.page, reporter=cls.reporter, category="OTHER", status=status,
                                      title=title, description="A description that is long enough to be valid.")
        Feedback.objects.create(page=cls.page, user=cls.fan, sentiment="POSITIVE", comment="Got my order fine.")
        Feedback.objects.create(page=cls.page, user=cls.critic, sentiment="NEGATIVE", comment="Hidden rude text",
                                is_hidden=True)
        recalculate_trust(cls.page)
        cls.url = reverse("reports:page_detail", args=[cls.page.pk])

    def test_page_renders_with_full_trust_badge(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/page_detail.html")
        self.assertContains(response, "Scores reflect community feedback and admin-verified reports only.")

    def test_reports_are_separated_into_verified_and_unverified_sections(self):
        response = self.client.get(self.url)
        self.assertEqual([r.title for r in response.context["verified_reports"]], ["Verified advance payment scam"])
        self.assertEqual(sorted(r.title for r in response.context["allegations"]),
                         ["Needs evidence fake product", "Pending non delivery claim"])
        self.assertContains(response, "Verified reports (1)")
        self.assertContains(response, "Unverified allegations (2)")

    def test_rejected_reports_and_hidden_feedback_are_never_shown(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "Rejected minor delay issue")
        self.assertNotContains(response, "Hidden rude text")
        self.assertContains(response, "Community feedback (1)")
        self.assertContains(response, "Got my order fine.")

    def test_people_are_shown_by_username_only(self):
        response = self.client.get(self.url)
        self.assertContains(response, "by reporter")
        self.assertNotContains(response, "reporter-private@example.com")

    def test_report_this_page_button_prefills_the_report_form(self):
        response = self.client.get(self.url)
        create_url = f"{reverse('reports:report_create')}?page={self.page.pk}"
        self.assertContains(response, f'href="{create_url}"')
        self.client.force_login(self.fan)
        form_page = self.client.get(create_url)
        self.assertContains(form_page, 'value="Trendy Closet"')
        self.assertContains(form_page, 'value="https://www.facebook.com/trendy.closet"')

    def test_prefill_ignores_invalid_page_parameter(self):
        self.client.force_login(self.fan)
        for value in ("abc", "99999", "1 OR 1=1"):
            with self.subTest(value=value):
                self.assertEqual(self.client.get(reverse("reports:report_create"), {"page": value}).status_code, 200)

    def test_page_with_only_rejected_reports_is_404_except_for_admins(self):
        hidden = FacebookPage.objects.create(name="Quiet Shop", url="facebook.com/quiet.shop")
        ScamReport.objects.create(page=hidden, reporter=self.reporter, category="OTHER", status=S.REJECTED,
                                  title="Rejected complaint title", description="A description that is long enough.")
        url = reverse("reports:page_detail", args=[hidden.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.fan)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_list_and_report_pages_link_to_page_detail(self):
        self.assertContains(self.client.get(reverse("reports:page_list")), f'href="{self.url}"')
        report = self.page.reports.get(status=S.APPROVED)
        self.assertContains(self.client.get(reverse("reports:report_detail", args=[report.pk])), f'href="{self.url}"')

    def test_unknown_page_is_404(self):
        self.assertEqual(self.client.get(reverse("reports:page_detail", args=[99999])).status_code, 404)
