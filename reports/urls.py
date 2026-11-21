from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("reports/new/", views.report_create, name="report_create"),
]
