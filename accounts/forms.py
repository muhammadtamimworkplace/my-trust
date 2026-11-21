from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.core.exceptions import ValidationError

from core.forms import BootstrapFormMixin

from .models import User


def clean_unique_email(raw_email, exclude_pk=None):
    """Normalize an email and reject it if another account already uses it (any letter case)."""
    email = User.objects.normalize_email(raw_email.strip())
    others = User.objects.filter(email__iexact=email)
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)
    if others.exists():
        raise ValidationError("An account with this email address already exists.", code="duplicate_email")
    return email


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Public sign-up form. Only username, email and password can be set here;
    the role always stays the default (USER), so nobody can register as an admin."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["email"].help_text = "Used only for your account. Never shown publicly."
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "autofocus": True})
        self.fields["email"].widget.attrs["autocomplete"] = "email"

    def clean_email(self):
        return clean_unique_email(self.cleaned_data["email"])


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Django's login form with Bootstrap styling."""


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Lets users edit their own name and email. Username and role are not editable here."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    def clean_email(self):
        return clean_unique_email(self.cleaned_data["email"], exclude_pk=self.instance.pk)


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    """Django's password change form with Bootstrap styling."""
