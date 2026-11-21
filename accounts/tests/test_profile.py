from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class ProfilePageTests(TestCase):
    url = reverse("accounts:profile")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("buyer", "buyer@example.com", "x", first_name="Rina", last_name="Akter")
        cls.other = User.objects.create_user("someone", "someone@example.com", "x")

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_shows_own_account_details(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertContains(response, "buyer@example.com")
        self.assertContains(response, "Rina Akter")
        self.assertContains(response, "Member")

    def test_never_shows_other_users_data_or_password_hash(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "someone@example.com")
        self.assertNotContains(response, "pbkdf2_sha256")

    def test_admin_role_is_labelled(self):
        self.user.role = User.Role.ADMIN
        self.user.save()
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), "Administrator")

    def test_navbar_username_links_to_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, f'href="{self.url}"')
