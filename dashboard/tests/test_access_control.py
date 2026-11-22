"""Access-control matrix for EVERY dashboard route (guide §12.3).

Routes are discovered from dashboard.urls, so a page added later is covered
automatically. For each route and each kind of visitor, with GET and POST:

    anonymous   -> 302 redirect to the login page
    member      -> 403 Forbidden (and nothing changes)
    administrator -> allowed (list pages return 200)
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.urls.converters import IntConverter

from dashboard import urls as dashboard_urls
from dashboard.models import AdminAction
from feedback.models import Comment, Feedback
from reports.models import FacebookPage, ScamReport

User = get_user_model()


def dashboard_routes():
    """(name, url) for every dashboard route, filling path parameters with an example value."""
    routes = []
    for pattern in dashboard_urls.urlpatterns:
        kwargs = {
            name: (1 if isinstance(converter, IntConverter) else "feedback")
            for name, converter in pattern.pattern.converters.items()
        }
        routes.append((pattern.name, reverse(f"dashboard:{pattern.name}", kwargs=kwargs), bool(kwargs)))
    return routes


class DashboardAccessControlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.member = User.objects.create_user("member", "member@example.com", "x")
        page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.report = ScamReport.objects.create(page=page, reporter=cls.member, category="OTHER",
                                               title="A report title here", description="A description that is long enough.")
        cls.feedback = Feedback.objects.create(page=page, user=cls.member, sentiment="NEGATIVE")
        cls.comment = Comment.objects.create(report=cls.report, user=cls.member, body="A comment")
        cls.routes = dashboard_routes()

    def snapshot(self):
        self.report.refresh_from_db()
        self.feedback.refresh_from_db()
        self.member.refresh_from_db()
        return (self.report.status, self.feedback.is_hidden, self.member.is_active, AdminAction.objects.count())

    def test_the_matrix_covers_every_dashboard_route(self):
        names = {name for name, _, _ in self.routes}
        self.assertTrue({"overview", "report_queue", "report_review", "page_list", "user_list", "user_toggle",
                         "moderation", "moderation_toggle", "activity"} <= names, names)
        self.assertGreaterEqual(len(self.routes), 9)

    def test_anonymous_visitors_are_sent_to_login_on_every_route_and_method(self):
        before = self.snapshot()
        for name, url, _ in self.routes:
            for method in ("get", "post"):
                with self.subTest(route=name, method=method):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response["Location"].startswith(reverse("accounts:login")), response["Location"])
        self.assertEqual(self.snapshot(), before)

    def test_members_get_403_on_every_route_and_method_and_nothing_changes(self):
        self.client.force_login(self.member)
        before = self.snapshot()
        for name, url, _ in self.routes:
            for method in ("get", "post"):
                with self.subTest(route=name, method=method):
                    response = getattr(self.client, method)(url, {"decision": "approve", "note": "x"})
                    self.assertEqual(response.status_code, 403)
        self.assertEqual(self.snapshot(), before)

    def test_administrators_can_open_every_list_page(self):
        self.client.force_login(self.admin)
        for name, url, has_args in self.routes:
            if not has_args:
                with self.subTest(route=name):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_administrators_can_open_detail_pages_and_post_only_routes_reject_get(self):
        self.client.force_login(self.admin)
        review = reverse("dashboard:report_review", args=[self.report.pk])
        self.assertEqual(self.client.get(review).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:user_toggle", args=[self.member.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("dashboard:moderation_toggle", args=["feedback", self.feedback.pk])).status_code, 405)

    def test_a_deactivated_administrator_loses_access(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 200)
        User.objects.filter(pk=self.admin.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 302)

    def test_demoting_an_administrator_removes_access_immediately(self):
        self.client.force_login(self.admin)
        User.objects.filter(pk=self.admin.pk).update(role=User.Role.USER)
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 403)
