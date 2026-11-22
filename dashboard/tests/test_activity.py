from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import AdminAction
from dashboard.services import activity_log
from reports.models import FacebookPage, ScamReport

User = get_user_model()
A = AdminAction.ActionType
URL = reverse("dashboard:activity")


class ActivityLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.member = User.objects.create_user("member", "member@example.com", "x")
        page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.report = ScamReport.objects.create(page=page, reporter=cls.member, category="OTHER",
                                               title="Logged report title", description="A description that is long enough.")
        cls.first = AdminAction.objects.create(admin=cls.admin, action_type=A.APPROVE_REPORT, report=cls.report, note="Looks right")
        cls.second = AdminAction.objects.create(admin=cls.admin, action_type=A.DEACTIVATE_USER, target_user=cls.member)

    def test_newest_first_and_filter_by_action(self):
        self.assertEqual(list(activity_log()), [self.second, self.first])
        self.assertEqual(list(activity_log(A.APPROVE_REPORT)), [self.first])
        self.assertEqual(list(activity_log("not-an-action")), [self.second, self.first])

    def test_page_shows_who_what_target_and_note(self):
        self.client.force_login(self.admin)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        for text in ("mod", "Approved report", "Logged report title", "Looks right", "Deactivated user", "member",
                     "2 entries.", "cannot be edited or deleted"):
            self.assertContains(response, text)
        self.assertContains(response, reverse("dashboard:report_review", args=[self.report.pk]))

    def test_filter_in_the_view_and_invalid_value_is_ignored(self):
        self.client.force_login(self.admin)
        response = self.client.get(URL, {"action": A.DEACTIVATE_USER})
        self.assertContains(response, "1 entry.")
        self.assertNotContains(response, "Logged report title")
        self.assertContains(self.client.get(URL, {"action": "<script>"}), "2 entries.")

    def test_pagination_keeps_filter(self):
        for i in range(30):
            AdminAction.objects.create(admin=self.admin, action_type=A.HIDE_COMMENT, note=f"n{i}")
        self.client.force_login(self.admin)
        response = self.client.get(URL, {"action": A.HIDE_COMMENT})
        self.assertEqual(len(response.context["page_obj"].object_list), 25)
        self.assertContains(response, "?action=HIDE_COMMENT&amp;page=2")

    def test_empty_log_and_access_control(self):
        AdminAction.objects.all().delete()
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(URL), "No activity recorded yet.")
        self.client.logout()
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(URL).status_code, 403)
