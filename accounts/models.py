from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """My Trust user account.

    Extends Django's built-in user (username, hashed password, names, active/staff
    flags, dates) with a unique email address and a platform role. Created before
    the first migration because switching user models later is very difficult.
    """

    class Role(models.TextChoices):
        USER = "USER", "User"
        ADMIN = "ADMIN", "Administrator"

    # Required and unique. The database collation (utf8mb4_unicode_ci) compares
    # case-insensitively, so "A@x.com" and "a@x.com" count as the same address.
    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)

    @property
    def is_platform_admin(self):
        """True for users allowed into the admin dashboard."""
        return self.role == self.Role.ADMIN or self.is_superuser

    def __str__(self):
        return self.username
