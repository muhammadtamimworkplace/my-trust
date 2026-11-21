from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()

VALID = {
    "username": "newbuyer",
    "email": "newbuyer@example.com",
    "password1": "Trust-me-2026!",
    "password2": "Trust-me-2026!",
}


class RegistrationTests(TestCase):
    url = reverse("accounts:register")

    def post(self, **overrides):
        return self.client.post(self.url, {**VALID, **overrides})

    def test_page_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")
        for name in ("username", "email", "password1", "password2"):
            self.assertContains(response, f'name="{name}"')

    def test_valid_registration_creates_user_logs_in_and_redirects(self):
        response = self.post()
        self.assertRedirects(response, reverse("core:home"))
        user = User.objects.get(username="newbuyer")
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_success_message_is_shown(self):
        response = self.client.post(self.url, VALID, follow=True)
        self.assertContains(response, "Your account has been created.")

    def test_cannot_register_as_admin_by_posting_role(self):
        self.post(role="ADMIN", is_staff="on", is_superuser="on")
        user = User.objects.get(username="newbuyer")
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user("existing", "NewBuyer@Example.com", "x")
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email address already exists.")
        self.assertFalse(User.objects.filter(username="newbuyer").exists())

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user("newbuyer", "other@example.com", "x")
        response = self.post()
        self.assertContains(response, "A user with that username already exists.")

    def test_email_is_required(self):
        response = self.post(email="")
        self.assertContains(response, "This field is required.")
        self.assertEqual(User.objects.count(), 0)

    def test_weak_password_is_rejected(self):
        response = self.post(password1="12345678", password2="12345678")
        self.assertContains(response, "This password is too common.")
        self.assertEqual(User.objects.count(), 0)

    def test_password_mismatch_is_rejected(self):
        response = self.post(password2="Different-2026!")
        self.assertContains(response, "The two password fields didn")
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_fields_are_marked_for_bootstrap(self):
        response = self.post(email="not-an-email")
        self.assertContains(response, "is-invalid")

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(User.objects.create_user("already", "a@example.com", "x"))
        self.assertRedirects(self.client.get(self.url), reverse("core:home"))

    def test_post_without_csrf_token_is_forbidden(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(self.url, VALID)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 0)
