from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from reports.models import FacebookPage
from reports.services import page_has_public_info

from .forms import FeedbackForm
from .models import Feedback
from .services import delete_feedback, save_feedback


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
