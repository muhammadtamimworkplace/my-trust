"""Helpers for the reports app."""
from urllib.parse import parse_qs, urlsplit

from django.core.exceptions import ValidationError

CANONICAL_PREFIX = "https://www.facebook.com/"

# Hostnames that serve the same Facebook pages (desktop, mobile, lite, short domain).
FACEBOOK_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "web.facebook.com",
    "mbasic.facebook.com",
    "touch.facebook.com",
    "fb.com",
    "www.fb.com",
}

MAX_URL_LENGTH = 255


def normalize_facebook_url(raw_url):
    """Return the single canonical form of a Facebook page/profile URL.

    The same page can be written many ways (m./web./fb.com hosts, http, upper case,
    trailing slash, tracking parameters, #fragments). Storing one canonical form lets
    the database's unique constraint prevent duplicate pages.

        "m.facebook.com/Example.Shop/?ref=abc" -> "https://www.facebook.com/example.shop"
        "facebook.com/profile.php?id=100012345" -> "https://www.facebook.com/profile.php?id=100012345"

    Raises ValidationError for anything that is not a Facebook page link.
    """
    value = (raw_url or "").strip()
    if not value:
        raise ValidationError("Enter the Facebook page link.", code="required")

    if "://" not in value:
        value = "https://" + value

    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() not in {"http", "https"} or host not in FACEBOOK_HOSTS:
        raise ValidationError(
            "Enter a facebook.com link, for example https://www.facebook.com/example.shop.",
            code="not_facebook",
        )

    path = parts.path.strip("/").lower()
    if not path:
        raise ValidationError("The link must point to a specific Facebook page, not the home page.", code="no_path")

    if path == "profile.php":
        # Pages without a username are identified only by their numeric id.
        page_id = parse_qs(parts.query).get("id", [""])[0]
        if not page_id.isdigit():
            raise ValidationError("This profile link is missing its numeric id (profile.php?id=…).", code="no_id")
        canonical = f"{CANONICAL_PREFIX}profile.php?id={page_id}"
    else:
        # Query strings and fragments are tracking/navigation details, not part of the page identity.
        canonical = CANONICAL_PREFIX + path

    if len(canonical) > MAX_URL_LENGTH:
        raise ValidationError("This link is too long.", code="too_long")
    return canonical
