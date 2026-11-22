from django import forms

from core.forms import BootstrapFormMixin

from .models import Comment, Feedback


class FeedbackForm(BootstrapFormMixin, forms.ModelForm):
    """A user's overall opinion of a page: positive or negative, with an optional comment."""

    sentiment = forms.ChoiceField(
        label="Your experience", choices=Feedback.Sentiment.choices, widget=forms.RadioSelect,
    )

    class Meta:
        model = Feedback
        fields = ["sentiment", "comment"]
        labels = {"comment": "Comment (optional)"}
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "maxlength": 1000})}


class CommentForm(BootstrapFormMixin, forms.ModelForm):
    """A discussion comment under a report."""

    class Meta:
        model = Comment
        fields = ["body"]
        labels = {"body": "Add a comment"}
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "maxlength": 1000, "placeholder": "Share what you know, politely."})}
