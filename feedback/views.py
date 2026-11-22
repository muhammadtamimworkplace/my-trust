from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from reports.models import FacebookPage, ScamReport
from reports.services import page_has_public_info

from .forms import CommentForm, FeedbackForm
from .models import Comment, Feedback, FeedbackVote
from .services import delete_feedback, save_feedback, vote_on_feedback


@login_required
@require_POST
def feedback_save(request, page_id):
    """Create or update the logged-in user's feedback on a page."""
    page = get_object_or_404(FacebookPage, pk=page_id)
    if not page_has_public_info(page) and not request.user.is_platform_admin:
        raise Http404("Page not found.")

    existing = Feedback.objects.filter(page=page, user=request.user).first()
    form = FeedbackForm(request.POST, instance=existing)
    if form.is_valid():
        _, created = save_feedback(
            user=request.user, page=page,
            sentiment=form.cleaned_data["sentiment"], comment=form.cleaned_data["comment"],
        )
        messages.success(request, "Thank you, your feedback was saved." if created else "Your feedback was updated.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("reports:page_detail", pk=page.pk)


@login_required
@require_POST
def feedback_delete(request, pk):
    """Delete the logged-in user's own feedback. Other users get 404, so existence is not revealed."""
    feedback = get_object_or_404(Feedback.objects.select_related("page"), pk=pk, user=request.user)
    page_id = feedback.page_id
    delete_feedback(feedback)
    messages.success(request, "Your feedback was deleted.")
    return redirect("reports:page_detail", pk=page_id)


@login_required
@require_POST
def comment_create(request, report_id):
    """Add a comment to a public report. Rejected reports cannot be discussed."""
    report = get_object_or_404(ScamReport, pk=report_id)
    if not report.is_public:
        raise Http404("Report not found.")

    form = CommentForm(request.POST)
    if form.is_valid():
        Comment.objects.create(report=report, user=request.user, body=form.cleaned_data["body"].strip())
        messages.success(request, "Your comment was posted.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("reports:report_detail", pk=report.pk)


VOTE_VALUES = {"like": FeedbackVote.Value.LIKE, "dislike": FeedbackVote.Value.DISLIKE}


@login_required
@require_POST
def feedback_vote(request, pk):
    """Like or dislike (toggle) another user's visible feedback."""
    feedback = get_object_or_404(Feedback.objects.select_related("page"), pk=pk, is_hidden=False)
    value = VOTE_VALUES.get(request.POST.get("value"))
    try:
        if value is None:
            raise ValidationError("Invalid vote.")
        vote_on_feedback(user=request.user, feedback=feedback, value=value)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("reports:page_detail", pk=feedback.page_id)
