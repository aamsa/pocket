from django import forms
from django.contrib.auth import get_user_model

from .models import (
    POCKET_COLOR_CHOICES,
    POCKET_ICON_CHOICES,
    POCKET_KIND_CASH,
    POCKET_KIND_CREDIT,
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
        fields = [
            "name",
            "kind",
            "parent",
            "icon",
            "color_token",
            "statement_day",
            "due_day",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": input_class, "autofocus": True}),
            "notes": forms.TextInput(attrs={"class": input_class, "placeholder": "Optional"}),
            "kind": forms.Select(attrs={"class": input_class, "x-model": "kind"}),
            "parent": forms.Select(attrs={"class": input_class}),
            "icon": forms.Select(attrs={"class": input_class}),
            "color_token": forms.Select(attrs={"class": input_class}),
            "statement_day": forms.NumberInput(
                attrs={
                    "class": input_class,
                    "min": 1,
                    "max": 28,
                    "inputmode": "numeric",
                    "placeholder": "1–28",
                }
            ),
            "due_day": forms.NumberInput(
                attrs={
                    "class": input_class,
                    "min": 1,
                    "max": 28,
                    "inputmode": "numeric",
                    "placeholder": "1–28",
                }
            ),
        }

    def __init__(self, *args, user=None, instance=None, **kwargs):
        self.user = user
        super().__init__(*args, instance=instance, **kwargs)
        # Parent dropdown: any of user's active CASH pockets except self/descendants.
        # Credit cards are flat — they cannot be a parent of anything either.
        qs = Pocket.objects.owned_by(user).active().cash()
        if instance and instance.pk:
            forbidden = set(instance.descendant_ids_with_self())
            qs = qs.exclude(pk__in=forbidden)
        self.fields["parent"].queryset = qs
        self.fields["parent"].empty_label = "— top level —"
        # Main pocket can't have its parent changed, can't switch kind.
        if instance and instance.is_main:
            self.fields["parent"].disabled = True
            self.fields["parent"].help_text = "Main pocket is always at the top level."
            self.fields["kind"].disabled = True
            self.fields["kind"].help_text = "Main is always a cash pocket."

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Name can't be blank.")
        return name

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind") or POCKET_KIND_CASH
        statement_day = cleaned.get("statement_day")
        due_day = cleaned.get("due_day")

        if kind == POCKET_KIND_CREDIT:
            if cleaned.get("parent") is not None:
                self.add_error("parent", "Credit cards aren't parented — leave this blank.")
            if self.instance and self.instance.is_main:
                self.add_error("kind", "The Main pocket can't be a credit card.")
            for fname, value in (("statement_day", statement_day), ("due_day", due_day)):
                if value is None:
                    self.add_error(fname, "Required for credit cards.")
                elif not (1 <= value <= 28):
                    self.add_error(fname, "Pick a day from 1 to 28.")
        else:  # cash — wipe any stray credit-only fields so the constraint passes
            cleaned["statement_day"] = None
            cleaned["due_day"] = None
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.owner_id is None:
            obj.owner = self.user
        if obj.kind != POCKET_KIND_CREDIT:
            obj.statement_day = None
            obj.due_day = None
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
