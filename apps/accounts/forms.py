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
    starting_balance = forms.DecimalField(
        max_digits=14,
        decimal_places=0,
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": input_class, "inputmode": "numeric", "placeholder": "0"}),
        label="Starting balance (Rp)",
        help_text="Your total money at the start of the date below. Balance runs forward from here.",
    )
    starting_balance_as_of = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": input_class, "type": "date"}, format="%Y-%m-%d"),
        label="As of",
    )

    def __init__(self, *args, profile=None, **kwargs):
        self.profile = profile
        if profile is not None and "initial" not in kwargs:
            kwargs["initial"] = {
                "display_name": profile.display_name,
                "starting_balance": profile.starting_balance,
                "starting_balance_as_of": profile.starting_balance_as_of,
            }
        super().__init__(*args, **kwargs)

    def save(self):
        self.profile.display_name = self.cleaned_data["display_name"].strip()
        self.profile.starting_balance = self.cleaned_data.get("starting_balance") or 0
        self.profile.starting_balance_as_of = self.cleaned_data.get("starting_balance_as_of")
        self.profile.save(
            update_fields=["display_name", "starting_balance", "starting_balance_as_of"]
        )
        return self.profile
