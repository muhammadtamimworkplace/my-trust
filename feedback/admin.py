from django.contrib import admin

from .models import Comment, Feedback, FeedbackVote


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("page", "user", "sentiment", "is_hidden", "created_at")
    list_filter = ("sentiment", "is_hidden")
    search_fields = ("page__name", "user__username", "comment")
    autocomplete_fields = ("page", "user")
    list_select_related = ("page", "user")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("report", "user", "is_hidden", "created_at")
    list_filter = ("is_hidden",)
    search_fields = ("body", "user__username", "report__title")
    autocomplete_fields = ("report", "user")
    list_select_related = ("report", "user")


@admin.register(FeedbackVote)
class FeedbackVoteAdmin(admin.ModelAdmin):
    list_display = ("feedback", "user", "value", "created_at")
    list_filter = ("value",)
    autocomplete_fields = ("feedback", "user")
    list_select_related = ("feedback__page", "feedback__user", "user")
