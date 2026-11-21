from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "Trust-me-2026!"


class ProfileEditTests(TestCase):
    url = reverse("accounts:profile_edit")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", PASSWORD)
        User.objects.create_user("taken", "taken@example.com", PASSWORD)

    def setUp(self):
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")

    def test_form_is_prefilled_with_current_values(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'value="buyer@example.com"')

    def test_valid_update_saves_and_redirects_with_message(self):
        response = self.client.post(
            self.url, {"first_name": "Rina", "last_name": "Akter", "email": "rina@example.com"}, follow=True
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertContains(response, "Your profile has been updated.")
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.email), ("Rina", "rina@example.com"))

    def test_keeping_own_email_is_allowed(self):
        response = self.client.post(self.url, {"first_name": "", "last_name": "", "email": "BUYER@example.com"})
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_email_of_another_account_is_rejected(self):
        response = self.client.post(self.url, {"first_name": "", "last_name": "", "email": "Taken@Example.com"})
        self.assertContains(response, "An account with this email address already exists.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "buyer@example.com")

    def test_cannot_change_role_or_username_through_this_form(self):
        self.client.post(self.url, {"email": "buyer@example.com", "role": "ADMIN", "username": "hacker"})
        self.user.refresh_from_db()
        self.assertEqual((self.user.username, self.user.role), ("buyer", User.Role.USER))


class PasswordChangeTests(TestCase):
    url = reverse("accounts:password_change")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", PASSWORD)

    def setUp(self):
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")

    def test_change_password_keeps_user_logged_in(self):
        new = "Brand-new-pass-77"
        response = self.client.post(
            self.url, {"old_password": PASSWORD, "new_password1": new, "new_password2": new}, follow=True
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertContains(response, "Your password has been changed.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_wrong_old_password_is_rejected(self):
        response = self.client.post(
            self.url, {"old_password": "wrong", "new_password1": "Brand-new-pass-77", "new_password2": "Brand-new-pass-77"}
        )
        self.assertContains(response, "Your old password was entered incorrectly.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_profile_page_links_to_edit_and_password_change(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, f'href="{reverse("accounts:profile_edit")}"')
        self.assertContains(response, f'href="{self.url}"')
