"""Shared test helpers for the reports app."""
import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

VALID_REPORT_POST = {
    "page_name": "Example Shop",
    "page_url": "https://m.facebook.com/Example.Shop/?ref=share",
    "category": "ADVANCE_PAYMENT",
    "title": "Paid in advance, never received",
    "description": "I paid 2,500 BDT by bKash for a dress. The seller blocked me afterwards.",
    "incident_date": "",
    "amount_lost": "2500",
}


def png_upload(name="shot.png"):
    """A small, genuinely valid PNG upload."""
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color=(15, 118, 110)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class TempMediaMixin:
    """Point MEDIA_ROOT at a temporary folder for the test class and remove it afterwards,
    so tests never write into the project's real media/ directory."""

    @classmethod
    def setUpClass(cls):
        cls._temp_media = tempfile.mkdtemp(prefix="mytrust-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media, ignore_errors=True)
