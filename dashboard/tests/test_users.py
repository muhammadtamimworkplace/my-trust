from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import AdminAction
from dashboard.services import search_users, toggle_user_active

User = get_user_model()
URL = reverse("dashboard:user_list")


class UserManagementBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "pw-12345!", role=User.Role.ADMIN)
        cls.root = User.objects.create_superuser("root", "root@example.com", "pw-12345!")
        cls.rina = User.objects.create_user("rina", "rina@example.com", "pw-12345!", first_name="Rina", last_name="Akter")
        cls.karim = User.objects.create_user("karim", "karim@example.com", "pw-12345!")

    def toggle_url(self, user):
        return reverse("dashboard:user_toggle", args=[user.pk])


class SearchUsersTests(UserManagementBase):
    def names(self, query=""):
        return {u.username for u in search_users(query)}

    def test_search_matches_username_email_and_names_partially(self):
        self.assertEqual(self.names("RIN"), {"rina"})
        self.assertEqual(self.names("karim@"), {"karim"})
        self.assertEqual(self.names("akter"), {"rina"})
        self.assertEqual(self.names(), {"mod", "root", "rina", "karim"})

    def test_report_count_is_annotated(self):
        self.assertTrue(all(hasattr(u, "report_count") for u in search_users()))


class ToggleServiceTests(UserManagementBase):
    def test_deactivate_then_activate_with_audit_entries(self):
        self.assertFalse(toggle_user_active(admin=self.admin, target=self.rina))
        self.rina.refresh_from_db()
        self.assertFalse(self.rina.is_active)
        self.assertTrue(toggle_user_active(admin=self.admin, target=self.rina))
        actions = list(AdminAction.objects.order_by("id").values_list("action_type", "admin", "target_user"))
        self.assertEqual(actions, [(AdminAction.ActionType.DEACTIVATE_USER, self.admin.pk, self.rina.pk),
                                   (AdminAction.ActionType.ACTIVATE_USER, self.admin.pk, self.rina.pk)])

    def test_cannot_deactivate_yourself_or_a_superuser(self):
        for target in (self.admin, self.root):
            with self.subTest(target=target.username), self.assertRaises(ValidationError):
                toggle_user_active(admin=self.admin, target=target)
            target.refresh_from_db()
            self.assertTrue(target.is_active)
        self.assertEqual(AdminAction.objects.count(), 0)


class UserViewTests(UserManagementBase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_list_shows_users_with_private_columns_for_admins(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        for text in ("rina@example.com", "Superuser", "Member", "Active"):
            self.assertContains(response, text)

    def test_search_filters_the_list(self):
        response = self.client.get(URL, {"q": "karim"})
        self.assertContains(response, "1 user.")
        self.assertNotContains(response, "rina@example.com")
        self.assertContains(self.client.get(URL, {"q": "nobody"}), "No users match your search.")

    def test_buttons_hidden_for_self_and_superusers(self):
        html = self.client.get(URL).content.decode()
        self.assertIn(self.toggle_url(self.rina), html)
        self.assertNotIn(self.toggle_url(self.admin), html)
        self.assertNotIn(self.toggle_url(self.root), html)

    def test_toggle_via_post_shows_message_and_returns_to_same_search(self):
        response = self.client.post(self.toggle_url(self.rina), {"next": f"{URL}?q=rina"}, follow=True)
        self.assertRedirects(response, f"{URL}?q=rina")
        self.assertContains(response, "rina is now deactivated.")

    def test_offsite_next_parameter_is_ignored(self):
        response = self.client.post(self.toggle_url(self.rina), {"next": "https://evil.example/"})
        self.assertRedirects(response, URL, fetch_redirect_response=False)

    def test_refused_toggles_show_an_error(self):
        self.assertContains(self.client.post(self.toggle_url(self.admin), follow=True), "You cannot deactivate your own account.")
        self.assertContains(self.client.post(self.toggle_url(self.root), follow=True), "Superuser accounts can only be changed")

    def test_deactivated_user_cannot_log_in_and_existing_session_stops_working(self):
        member = Client()
        self.assertTrue(member.login(username="karim", password="pw-12345!"))
        self.assertEqual(member.get(reverse("accounts:profile")).status_code, 200)
        self.client.post(self.toggle_url(self.karim))
        self.assertEqual(member.get(reverse("accounts:profile")).status_code, 302)  # session no longer valid
        self.assertFalse(Client().login(username="karim", password="pw-12345!"))

    def test_access_control_get_only_and_csrf(self):
        self.assertEqual(self.client.get(self.toggle_url(self.rina)).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.assertEqual(self.client.post(self.toggle_url(self.rina)).status_code, 302)
        self.client.force_login(self.rina)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.client.post(self.toggle_url(self.karim)).status_code, 403)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.admin)
        self.assertEqual(strict.post(self.toggle_url(self.rina)).status_code, 403)
        self.rina.refresh_from_db()
        self.assertTrue(self.rina.is_active)

    def test_pagination_keeps_search(self):
        for i in range(25):
            User.objects.create_user(f"bulk{i:02d}", f"bulk{i}@example.com", "x")
        response = self.client.get(URL, {"q": "bulk"})
        self.assertEqual(len(response.context["page_obj"].object_list), 20)
        self.assertContains(response, "?q=bulk&amp;page=2")
