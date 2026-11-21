"""Rebuild the trust score snapshot of every Facebook page.

    python manage.py recalculate_trust

Useful after changing the scoring constants in trustscore/services.py, after
restoring a database backup, or to repair scores edited outside the app.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from reports.models import FacebookPage
from trustscore.services import recalculate_trust


class Command(BaseCommand):
    help = "Recalculate the trust score of every Facebook page."

    def handle(self, *args, **options):
        with transaction.atomic():
            pages = list(FacebookPage.objects.all())
            for page in pages:
                recalculate_trust(page)
        self.stdout.write(self.style.SUCCESS(f"Recalculated trust scores for {len(pages)} page(s)."))
