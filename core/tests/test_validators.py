import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from core.validators import validate_file_size, validate_image_content, validate_image_extension


def image_bytes(fmt="PNG", size=(20, 20)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(15, 118, 110)).save(buffer, format=fmt)
    return buffer.getvalue()


class EvidenceValidatorTests(SimpleTestCase):
    def test_real_png_and_jpeg_pass_all_checks(self):
        for name, fmt in (("shot.png", "PNG"), ("shot.jpg", "JPEG"), ("shot.JPEG", "JPEG")):
            with self.subTest(name=name):
                upload = SimpleUploadedFile(name, image_bytes(fmt))
                validate_image_extension(upload)
                validate_file_size(upload)
                validate_image_content(upload)

    def test_disallowed_extensions_are_rejected(self):
        for name in ("payload.exe", "page.html", "script.php", "photo.gif", "doc.pdf", "noextension"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                validate_image_extension(SimpleUploadedFile(name, b"x"))

    def test_text_file_renamed_to_png_is_rejected(self):
        upload = SimpleUploadedFile("photo.png", b"<?php system($_GET['c']); ?>")
        with self.assertRaises(ValidationError) as ctx:
            validate_image_content(upload)
        self.assertEqual(ctx.exception.code, "invalid_image")

    def test_gif_renamed_to_png_is_rejected(self):
        upload = SimpleUploadedFile("photo.png", image_bytes("GIF"))
        with self.assertRaises(ValidationError) as ctx:
            validate_image_content(upload)
        self.assertEqual(ctx.exception.code, "invalid_image_format")

    def test_truncated_png_is_rejected(self):
        upload = SimpleUploadedFile("photo.png", image_bytes("PNG")[:40])
        with self.assertRaises(ValidationError):
            validate_image_content(upload)

    @override_settings(EVIDENCE_MAX_BYTES=1000)
    def test_file_over_size_limit_is_rejected_with_readable_message(self):
        upload = SimpleUploadedFile("big.png", b"0" * 1001)
        with self.assertRaises(ValidationError) as ctx:
            validate_file_size(upload)
        self.assertIn("maximum allowed size is 1000", ctx.exception.messages[0])

    @override_settings(EVIDENCE_MAX_BYTES=1000)
    def test_file_exactly_at_limit_is_allowed(self):
        validate_file_size(SimpleUploadedFile("ok.png", b"0" * 1000))

    def test_default_limit_is_five_megabytes(self):
        from django.conf import settings

        self.assertEqual(settings.EVIDENCE_MAX_BYTES, 5 * 1024 * 1024)
        self.assertEqual(settings.EVIDENCE_MAX_FILES, 5)

    def test_validation_leaves_file_position_unchanged(self):
        upload = SimpleUploadedFile("shot.png", image_bytes())
        upload.seek(5)
        validate_image_content(upload)
        self.assertEqual(upload.tell(), 5)
