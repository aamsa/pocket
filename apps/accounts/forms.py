from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
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


# --- Superadmin user management ---------------------------------------------


class BrandedSetPasswordForm(SetPasswordForm):
    """Set a user's password without the old one (admin reset). Styled to match."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", input_class)


class AdminUserCreateForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": input_class, "autocomplete": "off", "autofocus": True}),
    )
    display_name = forms.CharField(
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": input_class}),
        help_text="Defaults to the username.",
    )
    is_superuser = forms.BooleanField(
        required=False,
        label="Superuser (can manage other accounts)",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": input_class, "autocomplete": "new-password"}),
    )
    password_confirm = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"class": input_class, "autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("A user with that username already exists."))
        return username

    def clean(self):
        cleaned = super().clean()
        pw, pw2 = cleaned.get("password"), cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", _("The two passwords don't match."))
        if pw:
            try:
                validate_password(pw)
            except forms.ValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    def save(self):
        data = self.cleaned_data
        is_super = data.get("is_superuser", False)
        user = get_user_model().objects.create_user(
            username=data["username"],
            password=data["password"],
            is_staff=is_super,
            is_superuser=is_super,
        )
        # UserProfile is created by a post_save signal.
        profile = user.profile
        profile.display_name = (data.get("display_name") or "").strip() or data["username"]
        profile.force_password_change = True
        profile.save(update_fields=["display_name", "force_password_change"])
        return user
