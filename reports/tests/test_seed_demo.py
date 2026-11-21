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
