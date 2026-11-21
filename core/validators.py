"""Reusable upload validators (guide §12.2, file upload security)."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.template.defaultfilters import filesizeformat
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}

validate_image_extension = FileExtensionValidator(
    allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
    message="Only JPG and PNG images are allowed.",
)


def validate_file_size(file):
    """Reject files larger than settings.EVIDENCE_MAX_BYTES."""
    limit = settings.EVIDENCE_MAX_BYTES
    if file.size > limit:
        raise ValidationError(
            f"This file is {filesizeformat(file.size)}. The maximum allowed size is {filesizeformat(limit)}.",
            code="file_too_large",
        )


def validate_image_content(file):
    """Open the file with Pillow and accept it only if it really is a JPEG or PNG.

    The extension alone proves nothing: a script renamed to photo.png must be rejected.
    """
    position = file.tell() if hasattr(file, "tell") else None
    try:
        file.seek(0)
        with Image.open(file) as image:
            image_format = image.format
            image.verify()  # checks the file structure without decoding all pixels
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValidationError("This file is not a valid JPG or PNG image.", code="invalid_image") from exc
    finally:
        if position is not None:
            file.seek(position)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Only JPG and PNG images are allowed.", code="invalid_image_format")


EVIDENCE_VALIDATORS = [validate_image_extension, validate_file_size, validate_image_content]
