from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from reports.models import FacebookPage

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
