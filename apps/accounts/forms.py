from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _


input_class = (
    "w-full rounded-xl bg-brand-50 border border-brand-200 px-4 py-3 "
    "text-brand-900 placeholder-brand-400 focus:border-brand-500 "
    "focus:outline-none focus:ring-2 focus:ring-brand-300/40"
)


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": input_class, "autocomplete": "username", "autofocus": True}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": input_class, "autocomplete": "current-password"}
        ),
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        password = cleaned.get("password")
        if username and password:
            user = authenticate(self.request, username=username, password=password)
            if user is None:
                raise forms.ValidationError(_("Invalid username or password."))
            if not user.is_active:
                raise forms.ValidationError(_("This account is disabled."))
            self.user = user
        return cleaned


class BrandedPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", input_class)


class ProfileForm(forms.Form):
    display_name = forms.CharField(
        max_length=80,
        widget=forms.TextInput(attrs={"class": input_class}),
        label="Display name",
    )

    def __init__(self, *args, profile=None, **kwargs):
        self.profile = profile
        if profile is not None and "initial" not in kwargs:
            kwargs["initial"] = {"display_name": profile.display_name}
        super().__init__(*args, **kwargs)

    def save(self):
        self.profile.display_name = self.cleaned_data["display_name"].strip()
        self.profile.save(update_fields=["display_name"])
        return self.profile
