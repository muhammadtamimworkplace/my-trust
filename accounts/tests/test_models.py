from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

User = get_user_model()


class UserModelTests(TestCase):
    def test_project_uses_custom_user_model(self):
        self.assertEqual(User._meta.label, "accounts.User")
        self.assertEqual(User._meta.db_table, "accounts_user")

    def test_new_user_defaults_to_user_role(self):
        user = User.objects.create_user("alice", "alice@example.com", "S3cure-pass!")
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(user.is_platform_admin)

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"])
    def test_password_is_hashed_not_stored_in_plain_text(self):
        user = User.objects.create_user("bob", "bob@example.com", "S3cure-pass!")
        self.assertNotEqual(user.password, "S3cure-pass!")
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password("S3cure-pass!"))

    def test_admin_role_is_platform_admin(self):
        user = User.objects.create_user("carol", "carol@example.com", "x", role=User.Role.ADMIN)
        self.assertTrue(user.is_platform_admin)

    def test_superuser_is_platform_admin_even_without_admin_role(self):
        user = User.objects.create_superuser("root_admin", "root@example.com", "x")
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(user.is_platform_admin)

    def test_email_must_be_unique_case_insensitively(self):
        User.objects.create_user("dave", "dave@example.com", "x")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("dave2", "DAVE@example.com", "x")

    def test_str_returns_username(self):
        self.assertEqual(str(User(username="erin")), "erin")
