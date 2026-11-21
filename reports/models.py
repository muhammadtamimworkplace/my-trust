from django.conf import settings
from django.db import models

from .utils import normalize_facebook_url


class FacebookPage(models.Model):
    """A Facebook sales page that has been reported or reviewed on My Trust.

    `url` is always stored in canonical form (see normalize_facebook_url), so the
    unique constraint stops the same page from being added twice under different links.
    """

    name = models.CharField(max_length=150, db_index=True)
    url = models.URLField("Facebook URL", max_length=255, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pages_added",
        help_text="User who first added this page (kept even if that account is later removed).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Facebook page"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.url = normalize_facebook_url(self.url)
        super().save(*args, **kwargs)
