from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "Trust-me-2026!"


class LoginTests(TestCase):
    url = reverse("accounts:login")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", PASSWORD)

    def test_page_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_valid_credentials_log_in_and_redirect_home(self):
        response = self.client.post(self.url, {"username": "buyer", "password": PASSWORD})
        self.assertRedirects(response, reverse("core:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_wrong_password_shows_error_and_does_not_log_in(self):
        response = self.client.post(self.url, {"username": "buyer", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, {"username": "buyer", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_session_key_changes_on_login(self):
        self.client.get(self.url)
        self.client.session.save()
        before = self.client.session.session_key
        self.client.post(self.url, {"username": "buyer", "password": PASSWORD})
        self.assertNotEqual(self.client.session.session_key, before)

    def test_next_parameter_to_local_page_is_followed(self):
        response = self.client.post(
            f"{self.url}?next=/accounts/register/",
            {"username": "buyer", "password": PASSWORD, "next": "/accounts/register/"},
        )
        self.assertEqual(response["Location"], "/accounts/register/")

    def test_next_parameter_to_external_site_is_ignored(self):
        response = self.client.post(
            self.url, {"username": "buyer", "password": PASSWORD, "next": "https://evil.example/phish"}
        )
        self.assertRedirects(response, reverse("core:home"))

    def test_logged_in_user_visiting_login_is_redirected(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(self.url), reverse("core:home"))


class LogoutTests(TestCase):
    url = reverse("accounts:logout")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", PASSWORD)

    def setUp(self):
        self.client.force_login(self.user)

    def test_post_logs_out_and_redirects_home(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)


class NavbarAuthLinksTests(TestCase):
    def test_visitor_sees_login_and_register_links(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, f'href="{reverse("accounts:login")}"')
        self.assertContains(response, f'href="{reverse("accounts:register")}"')

    def test_logged_in_user_sees_logout_form_with_csrf(self):
        self.client.force_login(User.objects.create_user("buyer", "buyer@example.com", PASSWORD))
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, f'action="{reverse("accounts:logout")}"')
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertNotContains(response, f'href="{reverse("accounts:login")}"')
