"""Create (or remove) clearly fictional demo data for the thesis demonstration.

    python manage.py seed_demo            # create demo data (safe to run repeatedly)
    python manage.py seed_demo --reset    # remove demo data only, then exit

All demo pages use facebook.com/demo.* URLs and "(Demo)" names so they can never be
mistaken for real businesses. Demo accounts are prefixed "demo_". The demo password
comes from DEMO_USER_PASSWORD (.env); if it is missing, a random one is generated
and written to .env (never printed, never committed).
"""
import io
import os
import secrets
import string
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image, ImageDraw

from dashboard.models import AdminAction
from feedback.models import Comment, Feedback, FeedbackVote
from reports.models import Evidence, FacebookPage, ScamReport
from trustscore.services import recalculate_trust

User = get_user_model()
Cat = ScamReport.Category
St = ScamReport.Status

DEMO_USER_PREFIX = "demo_"
DEMO_URL_PREFIX = "https://www.facebook.com/demo."

USERS = [
    # username, first, last, role
    ("demo_admin", "Demo", "Administrator", User.Role.ADMIN),
    ("demo_rina", "Rina", "Akter", User.Role.USER),
    ("demo_karim", "Karim", "Hossain", User.Role.USER),
    ("demo_sadia", "Sadia", "Rahman", User.Role.USER),
    ("demo_tanvir", "Tanvir", "Ahmed", User.Role.USER),
    ("demo_nabila", "Nabila", "Islam", User.Role.USER),
]

PAGES = [
    # slug, display name
    ("trendy.closet", "Trendy Closet (Demo)"),
    ("gadget.bazaar", "Gadget Bazaar (Demo)"),
    ("organic.basket", "Organic Basket (Demo)"),
    ("luxe.watches", "Luxe Watches (Demo)"),
    ("kids.corner", "Kids Corner (Demo)"),
    ("shoe.planet", "Shoe Planet (Demo)"),
    ("beauty.hub", "Beauty Hub (Demo)"),
    ("home.decor", "Home Decor Studio (Demo)"),
]

# page slug, reporter, category, status, title, description, amount, days ago, evidence?
REPORTS = [
    ("trendy.closet", "demo_rina", Cat.ADVANCE_PAYMENT, St.APPROVED, "Took full advance payment, then blocked me",
     "I ordered two dresses and paid the full amount in advance by mobile banking. After payment the page stopped replying and blocked my account.", "3200", 21, True),
    ("trendy.closet", "demo_karim", Cat.NON_DELIVERY, St.APPROVED, "Order never delivered after three weeks",
     "Paid delivery charge and product price in advance. The courier tracking number they gave does not exist and the order never came.", "1850", 15, True),
    ("trendy.closet", "demo_sadia", Cat.HARASSMENT, St.PENDING, "Insulting messages after I asked for a refund",
     "When I asked about my missing order the page admin sent insulting voice messages and threatened to post my photo.", None, 4, False),
    ("gadget.bazaar", "demo_tanvir", Cat.FAKE_PRODUCT, St.APPROVED, "Received a fake smartwatch instead of original",
     "The post showed an original branded smartwatch with warranty. The parcel contained a cheap copy without any warranty card.", "4500", 30, True),
    ("gadget.bazaar", "demo_nabila", Cat.FAKE_PRODUCT, St.NEEDS_EVIDENCE, "Earbuds stopped working, looks like a copy",
     "The earbuds I received look different from the photos and stopped charging after two days. The page ignores my messages.", "1200", 6, False),
    ("gadget.bazaar", "demo_rina", Cat.OTHER, St.REJECTED, "Delivery was late by two days",
     "My order arrived two days later than promised. The product itself was fine but I was not informed about the delay.", None, 12, False),
    ("organic.basket", "demo_karim", Cat.NON_DELIVERY, St.PENDING, "Honey order not delivered yet",
     "I ordered organic honey ten days ago and paid in advance. They keep saying it will arrive tomorrow but nothing has come.", "950", 3, False),
    ("luxe.watches", "demo_sadia", Cat.IMPERSONATION, St.APPROVED, "Uses a famous watch brand's name and logo",
     "This page copies the logo, photos and name style of a well-known watch brand to look like an official reseller. The brand confirmed it is not affiliated.", None, 25, True),
    ("luxe.watches", "demo_tanvir", Cat.ADVANCE_PAYMENT, St.APPROVED, "Asked for 50% advance, then disappeared",
     "The page asked for a 50 percent advance to 'book' a watch. After I paid, the page deleted our chat and stopped responding.", "6000", 18, True),
    ("luxe.watches", "demo_nabila", Cat.ADVANCE_PAYMENT, St.PENDING, "Same advance payment trick happened to me",
     "I was also asked for an advance booking payment for a watch. After paying I was blocked. I have the payment receipt.", "5500", 2, False),
    ("kids.corner", "demo_rina", Cat.FAKE_PRODUCT, St.REJECTED, "Toy colour was different from the photo",
     "The toy car I received was blue instead of red as shown in the post. Otherwise it works, I just wanted to share this.", None, 9, False),
    ("shoe.planet", "demo_karim", Cat.FAKE_PRODUCT, St.APPROVED, "Leather shoes turned out to be synthetic",
     "The post said genuine leather shoes. What arrived is clearly synthetic material and the sole came off within a week.", "2700", 20, True),
    ("shoe.planet", "demo_sadia", Cat.NON_DELIVERY, St.NEEDS_EVIDENCE, "Paid but parcel marked as returned",
     "The courier shows my parcel as returned to sender although nobody contacted me. The page refuses to refund.", "2400", 5, False),
    ("beauty.hub", "demo_tanvir", Cat.FAKE_PRODUCT, St.PENDING, "Skincare product seems expired",
     "The face cream I received has no manufacturing date and smells strange. I am worried it is fake or expired.", "1100", 1, False),
    ("home.decor", "demo_nabila", Cat.OTHER, St.REJECTED, "Wrong size curtains delivered",
     "I received curtains in the wrong size. The page agreed to exchange them, so this is resolved now.", None, 14, False),
]

# page slug, user, sentiment, comment
FEEDBACK = [
    ("trendy.closet", "demo_tanvir", "NEGATIVE", "Same experience as others, avoid advance payment here."),
    ("trendy.closet", "demo_nabila", "NEGATIVE", "They blocked me too after payment."),
    ("trendy.closet", "demo_karim", "NEGATIVE", ""),
    ("gadget.bazaar", "demo_sadia", "POSITIVE", "My phone cover order was fine."),
    ("gadget.bazaar", "demo_karim", "NEGATIVE", "Got a copy product."),
    ("organic.basket", "demo_rina", "POSITIVE", "Received my order on time, good quality."),
    ("organic.basket", "demo_sadia", "POSITIVE", "Honest seller in my experience."),
    ("organic.basket", "demo_tanvir", "POSITIVE", ""),
    ("organic.basket", "demo_nabila", "NEGATIVE", "Delivery is slow."),
    ("kids.corner", "demo_karim", "POSITIVE", "Good toys, fast delivery."),
    ("kids.corner", "demo_sadia", "POSITIVE", "Recommended."),
    ("kids.corner", "demo_tanvir", "POSITIVE", ""),
    ("home.decor", "demo_rina", "POSITIVE", "They exchanged my item without problems."),
    ("home.decor", "demo_karim", "POSITIVE", ""),
    ("home.decor", "demo_sadia", "POSITIVE", "Nice products."),
    ("home.decor", "demo_tanvir", "NEGATIVE", "Packaging was poor."),
    ("luxe.watches", "demo_rina", "NEGATIVE", "Fake brand page, be careful."),
]

COMMENTS = [
    (0, "demo_tanvir", "Exactly the same thing happened to my cousin last month."),
    (0, "demo_nabila", "Thanks for reporting, I was about to order from them."),
    (3, "demo_sadia", "Did they give any warranty card at all?"),
    (7, "demo_rina", "Good catch, the logo looks almost identical."),
]


class Command(BaseCommand):
    help = "Create clearly fictional demo data (safe to re-run). Use --reset to remove it."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete demo data only, then exit.")
        parser.add_argument("--password", help="Password for demo accounts (default: DEMO_USER_PASSWORD from .env).")

    def handle(self, *args, **options):
        if options["reset"]:
            self.reset()
            return
        password = options["password"] or os.environ.get("DEMO_USER_PASSWORD") or self.generate_password()
        with transaction.atomic():
            counts = self.seed(password)
        self.stdout.write(self.style.SUCCESS("Demo data ready: " + ", ".join(f"{k} {v}" for k, v in counts.items())))
        self.stdout.write("Demo accounts: " + ", ".join(u[0] for u in USERS) + " (password: DEMO_USER_PASSWORD in .env)")

    # ---- creation -------------------------------------------------------------------------

    def seed(self, password):
        users = {}
        for username, first, last, role in USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@demo.mytrust.test", "first_name": first, "last_name": last, "role": role},
            )
            if created:
                user.set_password(password)
                user.save()
            users[username] = user

        pages = {}
        for slug, name in PAGES:
            pages[slug], _ = FacebookPage.objects.get_or_create(
                url=f"{DEMO_URL_PREFIX}{slug}", defaults={"name": name, "created_by": users["demo_rina"]}
            )

        admin = users["demo_admin"]
        now = timezone.now()
        reports = []
        for slug, reporter, category, status, title, description, amount, days_ago, with_evidence in REPORTS:
            report, created = ScamReport.objects.get_or_create(
                page=pages[slug], title=title,
                defaults={
                    "reporter": users[reporter], "category": category, "status": status, "description": description,
                    "amount_lost": Decimal(amount) if amount else None,
                    "incident_date": timezone.localdate() - timedelta(days=days_ago + 2),
                },
            )
            if created:
                # created_at is auto_now_add, so back-date it explicitly for realistic history.
                ScamReport.objects.filter(pk=report.pk).update(created_at=now - timedelta(days=days_ago))
                if status != St.PENDING:
                    self.record_decision(report, admin, status, now - timedelta(days=max(days_ago - 1, 0)))
                if with_evidence:
                    self.attach_demo_evidence(report)
            reports.append(report)

        for slug, username, sentiment, comment in FEEDBACK:
            Feedback.objects.get_or_create(
                page=pages[slug], user=users[username], defaults={"sentiment": sentiment, "comment": comment}
            )

        for report_index, username, body in COMMENTS:
            Comment.objects.get_or_create(report=reports[report_index], user=users[username], body=body)

        first_feedback = Feedback.objects.filter(page=pages["trendy.closet"], user=users["demo_tanvir"]).first()
        for voter in ("demo_rina", "demo_sadia"):
            FeedbackVote.objects.get_or_create(feedback=first_feedback, user=users[voter], defaults={"value": 1})

        for page in pages.values():
            recalculate_trust(page)

        return {
            "users": User.objects.filter(username__startswith=DEMO_USER_PREFIX).count(),
            "pages": FacebookPage.objects.filter(url__startswith=DEMO_URL_PREFIX).count(),
            "reports": ScamReport.objects.filter(page__url__startswith=DEMO_URL_PREFIX).count(),
            "evidence": Evidence.objects.filter(report__page__url__startswith=DEMO_URL_PREFIX).count(),
            "feedback": Feedback.objects.filter(page__url__startswith=DEMO_URL_PREFIX).count(),
            "comments": Comment.objects.filter(report__page__url__startswith=DEMO_URL_PREFIX).count(),
        }

    def record_decision(self, report, admin, status, when):
        action_type, note = {
            St.APPROVED: (AdminAction.ActionType.APPROVE_REPORT, "Evidence reviewed and consistent with the complaint."),
            St.REJECTED: (AdminAction.ActionType.REJECT_REPORT, "Not a scam: a service issue that was resolved or minor."),
            St.NEEDS_EVIDENCE: (AdminAction.ActionType.REQUEST_EVIDENCE, "Please upload a payment receipt or chat screenshot."),
        }[status]
        ScamReport.objects.filter(pk=report.pk).update(admin_note=note, reviewed_at=when)
        AdminAction.objects.create(admin=admin, action_type=action_type, report=report, note=note)

    def attach_demo_evidence(self, report):
        image = Image.new("RGB", (640, 360), color=(11, 31, 51))
        draw = ImageDraw.Draw(image)
        draw.rectangle([(16, 16), (623, 343)], outline=(15, 118, 110), width=4)
        draw.text((40, 60), "DEMO EVIDENCE - NOT A REAL SCREENSHOT", fill=(204, 251, 241))
        draw.text((40, 110), f"Report: {report.title[:48]}", fill=(255, 255, 255))
        draw.text((40, 150), f"Page: {report.page.name}", fill=(255, 255, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        Evidence.objects.create(
            report=report, file=ContentFile(buffer.getvalue(), name="demo-screenshot.png"),
            original_name="demo-screenshot.png",
        )

    # ---- password + reset -----------------------------------------------------------------

    def generate_password(self):
        password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        env_path = settings.BASE_DIR / ".env"
        with env_path.open("a", encoding="utf-8") as env_file:
            env_file.write(f"\n# Demo accounts created by seed_demo\nDEMO_USER_PASSWORD={password}\n")
        os.environ["DEMO_USER_PASSWORD"] = password
        self.stdout.write("Generated a demo password and saved it as DEMO_USER_PASSWORD in .env.")
        return password

    def reset(self):
        """Remove demo data only. A report counts as demo data if it is about a demo page
        OR was written by a demo account (e.g. while rehearsing the demo on a real page);
        otherwise that report would block deleting the demo account (PROTECT)."""
        demo_reports = ScamReport.objects.filter(
            Q(page__url__startswith=DEMO_URL_PREFIX) | Q(reporter__username__startswith=DEMO_USER_PREFIX)
        )
        with transaction.atomic():
            touched_real_pages = list(
                FacebookPage.objects.exclude(url__startswith=DEMO_URL_PREFIX)
                .filter(Q(reports__in=demo_reports) | Q(feedback__user__username__startswith=DEMO_USER_PREFIX))
                .distinct()
            )
            for evidence in Evidence.objects.filter(report__in=demo_reports):
                evidence.file.delete(save=False)  # remove the image file from media/
            AdminAction.objects.filter(admin__username__startswith=DEMO_USER_PREFIX).delete()
            AdminAction.objects.filter(report__in=demo_reports).delete()
            deleted_reports, _ = demo_reports.delete()  # cascades to evidence + comments
            FacebookPage.objects.filter(url__startswith=DEMO_URL_PREFIX).delete()  # cascades feedback
            deleted_users, _ = User.objects.filter(username__startswith=DEMO_USER_PREFIX).delete()
            for page in touched_real_pages:  # their counts changed: refresh the trust snapshot
                recalculate_trust(page)
        self.stdout.write(self.style.SUCCESS(f"Demo data removed ({deleted_reports} report-related rows, {deleted_users} user-related rows)."))
