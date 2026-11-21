from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import ProfileForm, RegistrationForm, StyledPasswordChangeForm


def register(request):
    """Create an account and log the new user in."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to My Trust, {user.username}! Your account has been created.")
            return redirect("core:home")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    """The logged-in user's own account page. Report history is added in P5-T03."""
    return render(request, "accounts/profile.html")


@login_required
def profile_edit(request):
    """Edit the logged-in user's own name and email."""
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})


class PasswordChangeView(SuccessMessageMixin, auth_views.PasswordChangeView):
    """Django's password change (keeps the user logged in) with a success message."""

    form_class = StyledPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Your password has been changed."
