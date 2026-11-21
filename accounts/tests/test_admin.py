from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser("boss", "boss@example.com", "x")
        cls.member = User.objects.create_user("member", "member@example.com", "x")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_changelist_shows_role_column_and_filter(self):
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "column-role")
        self.assertContains(response, "By role")

    def test_change_form_has_role_field(self):
        response = self.client.get(reverse("admin:accounts_user_change", args=[self.member.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="role"')

    def test_add_form_asks_for_email_and_role(self):
        response = self.client.get(reverse("admin:accounts_user_add"))
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="role"')

    def test_regular_user_cannot_open_admin(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response["Location"])
