from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.decorators import admin_required

User = get_user_model()


@admin_required
def protected_view(request):
    return HttpResponse("secret dashboard")


class AdminRequiredTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user("member", "member@example.com", "x")
        cls.admin = User.objects.create_user("admin1", "admin1@example.com", "x", role=User.Role.ADMIN)
        cls.superuser = User.objects.create_superuser("root1", "root1@example.com", "x")

    def call(self, user):
        request = RequestFactory().get("/dashboard/reports/?status=PENDING")
        request.user = user
        return protected_view(request)

    def test_anonymous_is_redirected_to_login_with_next(self):
        response = self.call(AnonymousUser())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/?next=/dashboard/reports/%3Fstatus%3DPENDING")

    def test_regular_user_gets_permission_denied(self):
        with self.assertRaises(PermissionDenied):
            self.call(self.member)

    def test_admin_role_is_allowed(self):
        self.assertContains(self.call(self.admin), "secret dashboard")

    def test_superuser_is_allowed(self):
        self.assertContains(self.call(self.superuser), "secret dashboard")

    def test_wrapped_view_keeps_its_name(self):
        self.assertEqual(protected_view.__name__, "protected_view")


class NavbarDashboardLinkTests(TestCase):
    def test_only_admins_see_dashboard_item(self):
        member = User.objects.create_user("member", "member@example.com", "x")
        admin = User.objects.create_user("admin1", "admin1@example.com", "x", role=User.Role.ADMIN)

        self.client.force_login(member)
        self.assertNotContains(self.client.get("/"), "Dashboard")

        self.client.force_login(admin)
        self.assertContains(self.client.get("/"), "Dashboard")
