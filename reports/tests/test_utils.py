from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from reports.utils import normalize_facebook_url

CANONICAL = "https://www.facebook.com/example.shop"


class NormalizeFacebookUrlTests(SimpleTestCase):
    def test_equivalent_links_become_one_canonical_url(self):
        variants = [
            "https://www.facebook.com/example.shop",
            "http://www.facebook.com/example.shop",
            "https://facebook.com/example.shop/",
            "facebook.com/example.shop",
            "www.facebook.com/example.shop",
            "https://m.facebook.com/Example.Shop/?ref=bookmarks",
            "https://web.facebook.com/example.shop?mibextid=ZbWKwL",
            "https://mbasic.facebook.com/example.shop#about",
            "https://fb.com/example.shop",
            "  HTTPS://WWW.FACEBOOK.COM/EXAMPLE.SHOP  ",
        ]
        for raw in variants:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_facebook_url(raw), CANONICAL)

    def test_profile_php_keeps_only_numeric_id(self):
        self.assertEqual(
            normalize_facebook_url("https://m.facebook.com/profile.php?id=100012345678&mibextid=abc"),
            "https://www.facebook.com/profile.php?id=100012345678",
        )

    def test_multi_segment_page_paths_are_kept(self):
        self.assertEqual(
            normalize_facebook_url("https://www.facebook.com/people/Example-Shop/100083000000000/"),
            "https://www.facebook.com/people/example-shop/100083000000000",
        )

    def test_rejected_inputs(self):
        cases = {
            "": "required",
            "   ": "required",
            "https://www.instagram.com/example.shop": "not_facebook",
            "https://facebook.com.evil.example/example.shop": "not_facebook",
            "https://evil.example/facebook.com/example.shop": "not_facebook",
            "ftp://facebook.com/example.shop": "not_facebook",
            "javascript:alert(1)": "not_facebook",
            "https://www.facebook.com/": "no_path",
            "https://www.facebook.com/profile.php": "no_id",
            "https://www.facebook.com/profile.php?id=abc": "no_id",
            "https://www.facebook.com/" + "a" * 300: "too_long",
        }
        for raw, code in cases.items():
            with self.subTest(raw=raw[:60]):
                with self.assertRaises(ValidationError) as ctx:
                    normalize_facebook_url(raw)
                self.assertEqual(ctx.exception.code, code)
