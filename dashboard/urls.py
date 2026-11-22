from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("reports/", views.report_queue_view, name="report_queue"),
    path("reports/<int:pk>/", views.report_review, name="report_review"),
    path("pages/", views.page_list, name="page_list"),
    path("moderation/", views.moderation, name="moderation"),
    path("moderation/<str:kind>/<int:pk>/toggle/", views.moderation_toggle, name="moderation_toggle"),
    path("activity/", views.activity, name="activity"),
    path("users/", views.user_list, name="user_list"),
    path("users/<int:pk>/toggle-active/", views.user_toggle_active, name="user_toggle"),
]
