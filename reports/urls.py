from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("pages/", views.page_list, name="page_list"),
    path("reports/new/", views.report_create, name="report_create"),
    path("reports/mine/", views.my_reports, name="my_reports"),
    path("reports/<int:pk>/", views.report_detail, name="report_detail"),
    path("reports/<int:pk>/evidence/add/", views.evidence_add, name="evidence_add"),
    path("evidence/<int:pk>/", views.evidence_file, name="evidence_file"),
]
