import io
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from dashboard.models import AdminAction
from feedback.models import Comment, Feedback
from reports.models import Evidence, FacebookPage, ScamReport

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp(prefix="mytrust-seed-media-")
TEST_PASSWORD = "Demo-test-pass-123"


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class SeedDemoCommandTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def run_command(self, *args):
        out = io.StringIO()
        call_command("seed_demo", *args, stdout=out)
        return out.getvalue()

    def counts(self):
        return (User.objects.count(), FacebookPage.objects.count(), ScamReport.objects.count(),
                Evidence.objects.count(), Feedback.objects.count(), Comment.objects.count(), AdminAction.objects.count())

    def test_creates_demo_data_covering_every_status(self):
        self.run_command("--password", TEST_PASSWORD)
        statuses = set(ScamReport.objects.values_list("status", flat=True))
        self.assertEqual(statuses, set(ScamReport.Status.values))
        self.assertEqual(User.objects.filter(role=User.Role.ADMIN, username="demo_admin").count(), 1)
        self.assertGreaterEqual(ScamReport.objects.count(), 15)
        self.assertGreater(Evidence.objects.count(), 0)

    def test_running_twice_creates_no_duplicates(self):
        self.run_command("--password", TEST_PASSWORD)
        first = self.counts()
        self.run_command("--password", TEST_PASSWORD)
        self.assertEqual(self.counts(), first)

    def test_all_demo_pages_are_clearly_fictional(self):
        self.run_command("--password", TEST_PASSWORD)
        for page in FacebookPage.objects.all():
            self.assertTrue(page.url.startswith("https://www.facebook.com/demo."), page.url)
            self.assertTrue(page.name.endswith("(Demo)"), page.name)

    def test_reviewed_reports_have_note_timestamp_and_audit_entry(self):
        self.run_command("--password", TEST_PASSWORD)
        reviewed = ScamReport.objects.exclude(status=ScamReport.Status.PENDING)
        for report in reviewed:
            self.assertTrue(report.admin_note)
            self.assertIsNotNone(report.reviewed_at)
            self.assertEqual(report.admin_actions.count(), 1)
        self.assertFalse(ScamReport.objects.filter(status=ScamReport.Status.PENDING, reviewed_at__isnull=False).exists())

    def test_demo_accounts_use_given_password_which_is_never_printed(self):
        output = self.run_command("--password", TEST_PASSWORD)
        self.assertTrue(User.objects.get(username="demo_rina").check_password(TEST_PASSWORD))
        self.assertNotIn(TEST_PASSWORD, output)

    def test_reset_removes_only_demo_data_and_its_files(self):
        real_user = User.objects.create_user("real_person", "real@example.com", "x")
        real_page = FacebookPage.objects.create(name="Real Shop", url="facebook.com/real.shop")
        self.run_command("--password", TEST_PASSWORD)
        stored_files = [Path(TEMP_MEDIA, e.file.name) for e in Evidence.objects.all()]
        self.assertTrue(all(f.exists() for f in stored_files))

        output = self.run_command("--reset")

        self.assertIn("Demo data removed", output)
        self.assertEqual(list(User.objects.all()), [real_user])
        self.assertEqual(list(FacebookPage.objects.all()), [real_page])
        self.assertEqual(ScamReport.objects.count() + Evidence.objects.count() + AdminAction.objects.count(), 0)
        self.assertFalse(any(f.exists() for f in stored_files))

    def test_reset_works_when_a_demo_user_reported_a_real_page(self):
        """Regression: during demo rehearsals a demo account may report a real page.
        That report used to block deleting the demo user (ProtectedError)."""
        self.run_command("--password", TEST_PASSWORD)
        real_page = FacebookPage.objects.create(name="Real Shop", url="facebook.com/real.shop")
        ScamReport.objects.create(page=real_page, reporter=User.objects.get(username="demo_rina"), category="OTHER",
                                  title="Rehearsal report title", description="Submitted while rehearsing the demo.")
        self.run_command("--reset")
        self.assertFalse(User.objects.filter(username__startswith="demo_").exists())
        self.assertFalse(ScamReport.objects.exists())
        self.assertEqual(list(FacebookPage.objects.all()), [real_page])  # real page itself is kept
        from trustscore.models import TrustEvaluation
        self.assertEqual(TrustEvaluation.objects.get(page=real_page).pending_report_count, 0)  # snapshot refreshed

    def test_generated_password_is_saved_to_env_file_and_never_printed(self):
        import os
        import re
        from unittest import mock

        with tempfile.TemporaryDirectory() as base, mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEMO_USER_PASSWORD", None)  # force generation; real .env is untouched
            with self.settings(BASE_DIR=Path(base)):
                output = self.run_command()
            env_text = Path(base, ".env").read_text(encoding="utf-8")
        match = re.search(r"^DEMO_USER_PASSWORD=([A-Za-z0-9]{16})$", env_text, flags=re.M)
        self.assertIsNotNone(match, env_text)
        password = match.group(1)
        self.assertNotIn(password, output)
        self.assertIn("saved it as DEMO_USER_PASSWORD in .env", output)
        self.assertTrue(User.objects.get(username="demo_admin").check_password(password))

    def test_empty_password_line_from_env_example_is_filled_in_place(self):
        import os
        import re
        from unittest import mock

        with tempfile.TemporaryDirectory() as base, mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEMO_USER_PASSWORD", None)
            Path(base, ".env").write_text("SECRET_KEY='x'\nDEMO_USER_PASSWORD=\nDB_PORT=3306\n", encoding="utf-8")
            with self.settings(BASE_DIR=Path(base)):
                self.run_command()
            lines = Path(base, ".env").read_text(encoding="utf-8").splitlines()
        demo_lines = [line for line in lines if line.startswith("DEMO_USER_PASSWORD=")]
        self.assertEqual(len(demo_lines), 1, lines)               # no duplicate appended
        self.assertRegex(demo_lines[0], r"^DEMO_USER_PASSWORD=[A-Za-z0-9]{16}$")
        self.assertEqual(lines[0], "SECRET_KEY='x'")              # other settings untouched
        self.assertEqual(lines[-1], "DB_PORT=3306")

    def test_existing_demo_accounts_are_synced_to_the_configured_password(self):
        """Regression (found in the fresh-install rehearsal): after re-cloning or restoring a
        database, .env may hold a new DEMO_USER_PASSWORD while the demo accounts still have the
        old one. seed_demo must make the accounts match .env, its single source of truth."""
        self.run_command("--password", "Old-demo-pass-1")
        self.run_command("--password", "New-demo-pass-2")
        for username in ("demo_admin", "demo_rina"):
            user = User.objects.get(username=username)
            self.assertTrue(user.check_password("New-demo-pass-2"), username)
            self.assertFalse(user.check_password("Old-demo-pass-1"), username)
        self.assertFalse(User.objects.get(username="demo_admin").check_password(""))

    def test_sync_never_touches_non_demo_accounts(self):
        real = User.objects.create_user("real_person", "real@example.com", "Real-pass-123")
        self.run_command("--password", TEST_PASSWORD)
        real.refresh_from_db()
        self.assertTrue(real.check_password("Real-pass-123"))
