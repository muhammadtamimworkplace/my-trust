"""Static audit of every template (P10-T01).

These rules were checked by hand in Phase 10; this test keeps them true as the
templates change. A failure names the file and the rule that was broken.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATE_DIR = Path(settings.BASE_DIR) / "templates"
ALL = sorted(TEMPLATE_DIR.rglob("*.html"))
# Full pages = everything except base layouts, partials and "_include" fragments.
PAGES = [p for p in ALL if "partials" not in p.parts and not p.name.startswith(("_", "base"))]


def text(path):
    return path.read_text(encoding="utf-8")


def rel(path):
    return path.relative_to(TEMPLATE_DIR).as_posix()


class TemplateAuditTests(SimpleTestCase):
    def assert_each(self, files, check, message):
        failures = [rel(p) for p in files if not check(text(p))]
        self.assertEqual(failures, [], message)

    def test_found_the_templates_and_the_patterns_actually_match(self):
        """Guards against the audit passing vacuously because a pattern stopped matching."""
        self.assertGreaterEqual(len(ALL), 30)
        self.assertGreaterEqual(len(PAGES), 19)
        everything = "".join(text(p) for p in ALL)
        self.assertGreaterEqual(len(re.findall(r'<form\b[^>]*method="post"[^>]*>', everything)), 10)
        self.assertGreaterEqual(len(re.findall(r"<button\b", everything)), 20)
        self.assertGreaterEqual(len(re.findall(r'target="_blank"', everything)), 3)

    def test_no_inline_styles(self):
        self.assert_each(ALL, lambda s: 'style="' not in s, "Use classes in static/css/main.css, not inline styles.")

    def test_every_image_has_alt_text(self):
        self.assert_each(ALL, lambda s: all("alt=" in tag for tag in re.findall(r"<img\b[^>]*>", s)),
                         "Every <img> needs an alt attribute.")

    def test_every_button_declares_its_type(self):
        self.assert_each(ALL, lambda s: all("type=" in tag for tag in re.findall(r"<button\b[^>]*>", s)),
                         'Every <button> needs type="submit" or type="button".')

    def test_every_post_form_has_a_csrf_token(self):
        def ok(s):
            forms = re.findall(r'<form\b[^>]*method="post"[^>]*>(.*?)</form>', s, flags=re.S | re.I)
            return all("{% csrf_token %}" in body for body in forms)
        self.assert_each(ALL, ok, "Every POST form must contain {% csrf_token %}.")

    def test_new_tab_links_use_noopener(self):
        self.assert_each(ALL, lambda s: all("noopener" in tag for tag in re.findall(r"<a\b[^>]*target=\"_blank\"[^>]*>", s)),
                         'Links with target="_blank" need rel="noopener".')

    def test_autoescaping_is_never_switched_off(self):
        self.assert_each(ALL, lambda s: "|safe" not in s and "{% autoescape off" not in s,
                         "Do not disable HTML escaping in templates (XSS risk).")

    def test_every_page_has_exactly_one_h1_and_a_title(self):
        self.assert_each(PAGES, lambda s: len(re.findall(r"<h1\b", s)) == 1, "Each page needs exactly one <h1>.")
        self.assert_each(PAGES, lambda s: re.search(r"\{% block (title|dashboard_title) %\}", s),
                         "Each page must set its own title block.")

    def test_tables_scroll_horizontally_on_small_screens(self):
        self.assert_each(ALL, lambda s: s.count("<table") <= s.count("table-responsive"),
                         'Wrap tables in <div class="table-responsive">.')
