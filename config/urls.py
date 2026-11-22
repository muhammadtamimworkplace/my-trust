"""Root URL configuration for My Trust.

Each app owns its routes in <app>/urls.py; they are included here under a namespace.
Media files are intentionally NOT served here: evidence goes through an
access-controlled view (guide §12.2).
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("", include("reports.urls")),  # /reports/…, /pages/…, /evidence/…
    path("", include("feedback.urls")),  # /pages/<id>/feedback/, …
]
