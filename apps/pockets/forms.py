from django import forms
from django.contrib.auth import get_user_model

from .models import (
    POCKET_COLOR_CHOICES,
    POCKET_ICON_CHOICES,
    SHARE_PERMISSION_CHOICES,
    Pocket,
    PocketShare,
)


input_class = (
    "w-full rounded-xl bg-brand-50 border border-brand-200 px-4 py-3 "
    "text-brand-900 placeholder-brand-400 focus:border-brand-500 "
    "focus:outline-none focus:ring-2 focus:ring-brand-300/40"
)


class PocketForm(forms.ModelForm):
    class Meta:
        model = Pocket
        fields = ["name", "parent", "icon", "color_token", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": input_class, "autofocus": True}),
            "notes": forms.TextInput(attrs={"class": input_class, "placeholder": "Optional"}),
            "parent": forms.Select(attrs={"class": input_class}),
            "icon": forms.Select(attrs={"class": input_class}),
            "color_token": forms.Select(attrs={"class": input_class}),
        }

    def __init__(self, *args, user=None, instance=None, **kwargs):
        self.user = user
        super().__init__(*args, instance=instance, **kwargs)
        # Parent dropdown: any of user's active pockets except self/descendants
        qs = Pocket.objects.owned_by(user).active()
        if instance and instance.pk:
            forbidden = set(instance.descendant_ids_with_self())
            qs = qs.exclude(pk__in=forbidden)
        self.fields["parent"].queryset = qs
        self.fields["parent"].empty_label = "— top level —"
        # Main pocket can't have its parent changed, can't be moved.
        if instance and instance.is_main:
            self.fields["parent"].disabled = True
            self.fields["parent"].help_text = "Main pocket is always at the top level."

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Name can't be blank.")
        return name

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.owner_id is None:
            obj.owner = self.user
        if commit:
            obj.save()
        return obj


class ShareInviteForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": input_class, "placeholder": "username", "autocomplete": "off"}
        ),
    )
    permission = forms.ChoiceField(
        choices=SHARE_PERMISSION_CHOICES,
        widget=forms.Select(attrs={"class": input_class}),
        initial="view",
    )

    def __init__(self, *args, pocket=None, inviter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pocket = pocket
        self.inviter = inviter

    def clean_username(self):
        User = get_user_model()
        username = self.cleaned_data["username"].strip()
        try:
            target = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError("No user with that username.")
        if target == self.inviter:
            raise forms.ValidationError("You can't share a pocket with yourself.")
        if target == self.pocket.owner:
            raise forms.ValidationError("That user already owns the pocket.")
        existing = PocketShare.objects.filter(
            pocket=self.pocket, shared_with=target
        ).exclude(status__in=["declined", "revoked"]).first()
        if existing:
            raise forms.ValidationError(
                "Already shared with that user (status: %s)." % existing.status
            )
        self.cleaned_data["target"] = target
        return username

    def save(self):
        target = self.cleaned_data["target"]
        return PocketShare.objects.create(
            pocket=self.pocket,
            invited_by=self.inviter,
            shared_with=target,
            permission=self.cleaned_data["permission"],
        )
