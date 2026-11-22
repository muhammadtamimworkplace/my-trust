"""Security settings and the HTTP behaviour they produce (P11-T01)."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from reports.tests.helpers import VALID_REPORT_POST, TempMediaMixin, png_upload

User = get_user_model()


class SecurityHeaderTests(TestCase):
    def test_every_page_sends_protective_headers(self):
        for url in ("/", "/pages/", "/accounts/login/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response["X-Frame-Options"], "DENY")
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                self.assertEqual(response["Referrer-Policy"], "same-origin")
                self.assertEqual(response["Cross-Origin-Opener-Policy"], "same-origin")


class CookieTests(TestCase):
    def test_session_and_csrf_cookies_are_httponly_and_samesite(self):
        User.objects.create_user("buyer", "buyer@example.com", "Trust-me-2026!")
        client = Client()
        client.get("/accounts/login/")  # sets the CSRF cookie
        csrf = client.cookies[settings.CSRF_COOKIE_NAME]
        self.assertTrue(csrf["httponly"])
        self.assertEqual(csrf["samesite"], "Lax")
        client.post("/accounts/login/", {"username": "buyer", "password": "Trust-me-2026!"})
        session = client.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(session["httponly"])
        self.assertEqual(session["samesite"], "Lax")
        self.assertEqual(int(session["max-age"]), 60 * 60 * 24 * 7)

    def test_https_only_flags_are_off_for_the_local_http_demo(self):
        self.assertFalse(settings.HTTPS)
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertFalse(settings.SECURE_SSL_REDIRECT)
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)


class PasswordHasherTests(TestCase):
    def test_application_uses_pbkdf2_and_only_tests_use_the_fast_hasher(self):
        self.assertEqual(settings.PRODUCTION_PASSWORD_HASHERS, ["django.contrib.auth.hashers.PBKDF2PasswordHasher"])
        self.assertTrue(settings.RUNNING_TESTS)
        self.assertEqual(settings.PASSWORD_HASHERS, ["django.contrib.auth.hashers.MD5PasswordHasher"])


class UploadLimitTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("buyer", "buyer@example.com", "x"))

    def test_six_to_ten_files_get_the_friendly_form_error(self):
        files = [png_upload(f"s{i}.png") for i in range(6)]
        response = self.client.post("/reports/new/", {**VALID_REPORT_POST, "evidence": files})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at most 5 files")

    def test_more_than_the_hard_limit_is_refused_outright(self):
        files = [png_upload(f"s{i}.png") for i in range(settings.DATA_UPLOAD_MAX_NUMBER_FILES + 1)]
        response = self.client.post("/reports/new/", {**VALID_REPORT_POST, "evidence": files})
        self.assertEqual(response.status_code, 400)


class LoggingTests(TestCase):
    def test_app_loggers_are_configured(self):
        for app in ("reports", "dashboard", "feedback"):
            self.assertIn(app, settings.LOGGING["loggers"])
