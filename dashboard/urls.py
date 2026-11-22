from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("reports/", views.report_queue_view, name="report_queue"),
    path("reports/<int:pk>/", views.report_review, name="report_review"),
]
