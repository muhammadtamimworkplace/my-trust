import io
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path, PurePath

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from reports.models import Evidence, FacebookPage, ScamReport, evidence_upload_path

User = get_user_model()


class FacebookPageModelTests(TestCase):
    def test_url_is_stored_in_canonical_form(self):
        page = FacebookPage.objects.create(name="  Example Shop ", url="m.facebook.com/Example.Shop/?ref=x")
        page.refresh_from_db()
        self.assertEqual(page.url, "https://www.facebook.com/example.shop")
        self.assertEqual(page.name, "Example Shop")

    def test_same_page_under_a_different_link_is_rejected(self):
        FacebookPage.objects.create(name="Example Shop", url="https://www.facebook.com/example.shop")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FacebookPage.objects.create(name="Example Shop copy", url="fb.com/EXAMPLE.SHOP/")

    def test_invalid_url_cannot_be_saved(self):
        with self.assertRaises(ValidationError):
            FacebookPage.objects.create(name="Not Facebook", url="https://example.com/shop")
        self.assertEqual(FacebookPage.objects.count(), 0)

    def test_creator_is_kept_as_null_when_user_is_deleted(self):
        user = User.objects.create_user("adder", "adder@example.com", "x")
        page = FacebookPage.objects.create(name="Shop", url="facebook.com/shop1", created_by=user)
        user.delete()
        page.refresh_from_db()
        self.assertIsNone(page.created_by)

    def test_str_and_default_ordering(self):
        FacebookPage.objects.create(name="Zeta Store", url="facebook.com/zeta")
        FacebookPage.objects.create(name="Alpha Store", url="facebook.com/alpha")
        self.assertEqual([str(p) for p in FacebookPage.objects.all()], ["Alpha Store", "Zeta Store"])


class ScamReportModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("reporter", "reporter@example.com", "x")
        cls.page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")

    def make_report(self, **overrides):
        data = {
            "page": self.page,
            "reporter": self.user,
            "category": ScamReport.Category.ADVANCE_PAYMENT,
            "title": "Paid in advance, never received",
            "description": "I paid 2,500 BDT by bKash for a dress. The seller blocked me afterwards.",
        }
        data.update(overrides)
        return ScamReport(**data)

    def test_new_report_is_pending_and_not_verified(self):
        report = self.make_report()
        report.full_clean()
        report.save()
        self.assertEqual(report.status, ScamReport.Status.PENDING)
        self.assertEqual(report.get_status_display(), "Under review")
        self.assertFalse(report.is_verified)

    def test_approved_report_is_verified(self):
        report = self.make_report(status=ScamReport.Status.APPROVED)
        self.assertTrue(report.is_verified)
        self.assertEqual(report.get_status_display(), "Verified by admin")

    def test_field_validation_rules(self):
        cases = {
            "title": {"title": "Too short"},
            "description": {"description": "Not enough detail."},
            "incident_date": {"incident_date": timezone.localdate() + timedelta(days=1)},
            "amount_lost": {"amount_lost": Decimal("-1.00")},
            "category": {"category": "NOT_A_CATEGORY"},
        }
        for field, overrides in cases.items():
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    self.make_report(**overrides).full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_today_and_zero_amount_are_allowed(self):
        self.make_report(incident_date=timezone.localdate(), amount_lost=Decimal("0")).full_clean()

    def test_database_rejects_negative_amount_even_without_form_validation(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_report(amount_lost=Decimal("-5.00")).save()

    def test_page_with_reports_cannot_be_deleted(self):
        self.make_report().save()
        with self.assertRaises(ProtectedError):
            self.page.delete()

    def test_reporter_with_reports_cannot_be_deleted(self):
        self.make_report().save()
        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_newest_reports_come_first(self):
        first = self.make_report()
        first.save()
        second = self.make_report(title="Second report about this page")
        second.save()
        self.assertEqual(list(ScamReport.objects.all()), [second, first])


TEMP_MEDIA = tempfile.mkdtemp(prefix="mytrust-test-media-")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EvidenceModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user("reporter", "reporter@example.com", "x")
        page = FacebookPage.objects.create(name="Example Shop", url="facebook.com/example.shop")
        cls.report = ScamReport.objects.create(
            page=page, reporter=user, category=ScamReport.Category.FAKE_PRODUCT,
            title="Received a fake copy", description="The product shown was original but a copy arrived.",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def png_upload(self, name="My Screenshot.PNG"):
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def test_saved_file_gets_random_name_and_keeps_original_for_display(self):
        evidence = Evidence.objects.create(report=self.report, file=self.png_upload())
        stored = PurePath(evidence.file.name)
        today = timezone.localdate()
        self.assertEqual(stored.parent.as_posix(), f"evidence/{today:%Y}/{today:%m}")
        self.assertRegex(stored.name, r"^[0-9a-f]{32}\.png$")
        self.assertEqual(evidence.original_name, "My Screenshot.PNG")
        self.assertGreater(evidence.size_bytes, 0)
        self.assertTrue(Path(TEMP_MEDIA, evidence.file.name).exists())

    def test_two_uploads_with_the_same_name_do_not_collide(self):
        first = Evidence.objects.create(report=self.report, file=self.png_upload("same.png"))
        second = Evidence.objects.create(report=self.report, file=self.png_upload("same.png"))
        self.assertNotEqual(first.file.name, second.file.name)

    def test_jpeg_extension_is_normalised_to_jpg(self):
        self.assertTrue(evidence_upload_path(None, "photo.JPEG").endswith(".jpg"))

    def test_model_validation_rejects_fake_image(self):
        evidence = Evidence(report=self.report, file=SimpleUploadedFile("evil.png", b"not an image"))
        with self.assertRaises(ValidationError) as ctx:
            evidence.full_clean()
        self.assertIn("file", ctx.exception.message_dict)

    def test_evidence_is_deleted_with_its_report(self):
        Evidence.objects.create(report=self.report, file=self.png_upload())
        self.report.delete()
        self.assertEqual(Evidence.objects.count(), 0)
