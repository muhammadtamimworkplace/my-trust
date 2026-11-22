"""Custom error pages (P10-T03). The test runner uses DEBUG=False, so these are the real pages."""
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.views.defaults import server_error

User = get_user_model()


class ErrorPageTests(TestCase):
    def test_404_page_for_unknown_url_and_missing_objects(self):
        for url in ("/this-does-not-exist/", reverse("reports:page_detail", args=[99999])):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertTemplateUsed(response, "404.html")
                self.assertContains(response, "Page not found", status_code=404)

    def test_403_page_for_non_admin_on_dashboard(self):
        self.client.force_login(User.objects.create_user("member", "member@example.com", "x"))
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")
        self.assertContains(response, "You don't have access to this page", status_code=403)

    def test_500_page_renders_standalone_without_request_context(self):
        response = server_error(RequestFactory().get("/"))
        html = response.content.decode()
        self.assertEqual(response.status_code, 500)
        self.assertIn("Something went wrong", html)
        self.assertIn("/static/css/main.css", html)
        self.assertNotIn("Traceback", html)

    def test_csrf_failure_page_explains_what_to_do(self):
        strict = Client(enforce_csrf_checks=True)
        response = strict.post(reverse("accounts:login"), {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Please try again", status_code=403)
        self.assertNotContains(response, "CSRF verification failed", status_code=403)

    def test_error_pages_reveal_no_technical_details(self):
        response = self.client.get("/missing-page/")
        for leak in ("Traceback", "settings.py", "DEBUG", "urlpatterns"):
            self.assertNotContains(response, leak, status_code=404)
