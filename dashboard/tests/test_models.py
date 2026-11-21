from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from dashboard.models import AdminAction
from reports.models import FacebookPage, ScamReport

User = get_user_model()


class AdminActionModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("mod", "mod@example.com", "x", role=User.Role.ADMIN)
        cls.member = User.objects.create_user("member", "member@example.com", "x")
        page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.report = ScamReport.objects.create(
            page=page, reporter=cls.member, category=ScamReport.Category.IMPERSONATION,
            title="Copies a known brand", description="Uses the logo and name of a well-known brand shop.",
        )

    def test_report_decision_is_logged(self):
        action = AdminAction.objects.create(
            admin=self.admin, action_type=AdminAction.ActionType.APPROVE_REPORT, report=self.report, note="Evidence clear."
        )
        self.assertEqual(list(self.report.admin_actions.all()), [action])
        self.assertEqual(list(self.admin.admin_actions.all()), [action])
        self.assertIn("Approved report", str(action))

    def test_feedback_target_is_stored_by_type_and_id(self):
        action = AdminAction.objects.create(
            admin=self.admin, action_type=AdminAction.ActionType.HIDE_FEEDBACK,
            target_type=AdminAction.TargetType.FEEDBACK, target_id=42,
        )
        self.assertEqual((action.target_type, action.target_id), ("FEEDBACK", 42))

    def test_log_entry_survives_deletion_of_target_user(self):
        target = User.objects.create_user("spammer", "spam@example.com", "x")
        action = AdminAction.objects.create(
            admin=self.admin, action_type=AdminAction.ActionType.DEACTIVATE_USER, target_user=target
        )
        target.delete()
        action.refresh_from_db()
        self.assertIsNone(action.target_user)

    def test_admin_with_logged_actions_cannot_be_deleted(self):
        AdminAction.objects.create(admin=self.admin, action_type=AdminAction.ActionType.REJECT_REPORT)
        with self.assertRaises(ProtectedError):
            self.admin.delete()

    def test_newest_entries_first(self):
        first = AdminAction.objects.create(admin=self.admin, action_type="APPROVE_REPORT")
        second = AdminAction.objects.create(admin=self.admin, action_type="REJECT_REPORT")
        self.assertEqual(list(AdminAction.objects.all()), [second, first])
