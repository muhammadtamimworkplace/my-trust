from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from core.forms import BootstrapFormMixin

from .models import User


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
        email = User.objects.normalize_email(self.cleaned_data["email"].strip())
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.", code="duplicate_email")
        return email


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Django's login form with Bootstrap styling."""

