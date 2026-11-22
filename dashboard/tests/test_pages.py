from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.services import admin_pages
from feedback.models import Feedback
from reports.models import FacebookPage, ScamReport
from trustscore.services import recalculate_trust

User = get_user_model()
S = ScamReport.Status
URL = reverse("dashboard:page_list")


class AdminPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "x")
        cls.fan = User.objects.create_user("fan", "fan@example.com", "x")
        cls.busy = FacebookPage.objects.create(name="Busy Shop", url="facebook.com/busy.shop")
        cls.hidden = FacebookPage.objects.create(name="Hidden Shop", url="facebook.com/hidden.shop")
        cls.empty = FacebookPage.objects.create(name="Empty Shop", url="facebook.com/empty.shop")
        for page, status in [(cls.busy, S.APPROVED), (cls.busy, S.APPROVED), (cls.busy, S.PENDING),
                             (cls.busy, S.NEEDS_EVIDENCE), (cls.busy, S.REJECTED), (cls.hidden, S.REJECTED)]:
            ScamReport.objects.create(page=page, reporter=cls.user, category="OTHER", status=status,
                                      title="A report title here", description="A description that is long enough.")
        Feedback.objects.create(page=cls.busy, user=cls.user, sentiment="NEGATIVE")
        Feedback.objects.create(page=cls.busy, user=cls.fan, sentiment="POSITIVE")
        recalculate_trust(cls.busy)

    def row(self, page):
        return admin_pages().get(pk=page.pk)

    def test_counts_are_correct_even_with_reports_and_feedback_joined(self):
        busy = self.row(self.busy)
        self.assertEqual((busy.total_reports, busy.verified_reports, busy.review_reports, busy.rejected_reports,
                          busy.feedback_count), (5, 2, 2, 1, 2))

    def test_lists_every_page_including_hidden_and_empty_ones(self):
        self.assertEqual([p.name for p in admin_pages()], ["Busy Shop", "Hidden Shop", "Empty Shop"])
        self.assertEqual(self.row(self.hidden).rejected_reports, 1)

    def test_search_by_name_or_link_part(self):
        self.assertEqual([p.name for p in admin_pages("hidden")], ["Hidden Shop"])
        self.assertEqual([p.name for p in admin_pages("facebook.com/busy")], ["Busy Shop"])

    def test_view_renders_rows_and_note_about_hidden_pages(self):
        self.client.force_login(self.admin)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "3 pages.")
        self.assertContains(response, "Hidden Shop")
        self.assertContains(response, "Includes pages hidden from the public")
        self.assertContains(response, f'href="{reverse("reports:page_detail", args=[self.hidden.pk])}"')

    def test_view_search_and_empty_result(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(URL, {"q": "busy"}), "1 page.")
        self.assertContains(self.client.get(URL, {"q": "zzz"}), "No pages match your search.")

    def test_admin_can_open_a_hidden_page_that_the_public_cannot(self):
        detail = reverse("reports:page_detail", args=[self.hidden.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_access_control(self):
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(URL).status_code, 403)
