from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path("pages/<int:page_id>/feedback/", views.feedback_save, name="feedback_save"),
]
