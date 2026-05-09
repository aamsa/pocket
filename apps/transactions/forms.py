from datetime import date

from django import forms

from apps.pockets.models import Pocket
from apps.pockets.permissions import can_manage


def _manageable_pockets(user):
    """All active pockets the user can write to: owned + shared with manage."""
    owned = list(Pocket.objects.owned_by(user).active())
    shared = [p for p in Pocket.objects.active() if not p.owner_id == user.id and can_manage(user, p)]
    ids = [p.id for p in owned + shared]
    return Pocket.objects.filter(pk__in=ids).select_related("owner")

from .models import (
    CATEGORY_KIND_INCOME,
    FREQUENCY_CHOICES,
    TXN_KIND_CHOICES,
    Category,
    RecurringRule,
    Transaction,
    Transfer,
)


input_class = (
    "w-full rounded-xl bg-brand-50 border border-brand-200 px-4 py-3 "
    "text-brand-900 placeholder-brand-400 focus:border-brand-500 "
    "focus:outline-none focus:ring-2 focus:ring-brand-300/40"
)


class TransactionForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=0,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": input_class, "inputmode": "numeric", "placeholder": "0"}
        ),
        label="Amount",
    )

    class Meta:
        model = Transaction
        fields = ["pocket", "kind", "amount", "category", "occurred_on", "notes"]
        widgets = {
            "pocket": forms.Select(attrs={"class": input_class}),
            "kind": forms.HiddenInput(),
            "category": forms.Select(attrs={"class": input_class}),
            "occurred_on": forms.DateInput(
                attrs={"class": input_class, "type": "date"}
            ),
            "notes": forms.TextInput(
                attrs={"class": input_class, "placeholder": "Optional"}
            ),
        }

    def __init__(self, *args, user=None, kind=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if kind and not self.is_bound:
            self.initial["kind"] = kind
        if not self.is_bound and not self.initial.get("occurred_on"):
            self.initial["occurred_on"] = date.today().isoformat()

        chosen_kind = self.initial.get("kind") or self.data.get("kind") or kind
        if user is not None:
            self.fields["pocket"].queryset = _manageable_pockets(user)
            cat_qs = Category.objects.for_user(user).active()
            if chosen_kind:
                cat_qs = cat_qs.filter(kind=chosen_kind)
            self.fields["category"].queryset = cat_qs

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.created_by_id is None:
            obj.created_by = self.user
        if commit:
            obj.save()
        return obj


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "kind", "icon", "color_token"]
        widgets = {
            "name": forms.TextInput(attrs={"class": input_class, "autofocus": True}),
            "kind": forms.Select(attrs={"class": input_class}),
            "icon": forms.Select(attrs={"class": input_class}),
            "color_token": forms.Select(attrs={"class": input_class}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.created_by_id is None:
            obj.created_by = self.user
        obj.is_default = False
        if commit:
            obj.save()
        return obj


class TransferForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=0,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": input_class, "inputmode": "numeric", "placeholder": "0"}
        ),
    )

    class Meta:
        model = Transfer
        fields = ["from_pocket", "to_pocket", "amount", "occurred_on", "notes"]
        widgets = {
            "from_pocket": forms.Select(attrs={"class": input_class}),
            "to_pocket": forms.Select(attrs={"class": input_class}),
            "occurred_on": forms.DateInput(attrs={"class": input_class, "type": "date"}),
            "notes": forms.TextInput(
                attrs={"class": input_class, "placeholder": "Optional"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get("occurred_on"):
            self.initial["occurred_on"] = date.today().isoformat()
        if user is not None:
            qs = _manageable_pockets(user)
            self.fields["from_pocket"].queryset = qs
            self.fields["to_pocket"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        f, t = cleaned.get("from_pocket"), cleaned.get("to_pocket")
        if f and t and f == t:
            raise forms.ValidationError("From and To must be different pockets.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.created_by_id is None:
            obj.created_by = self.user
        if commit:
            obj.save()
        return obj


class RecurringRuleForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=0,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": input_class, "inputmode": "numeric", "placeholder": "0"}
        ),
    )
    interval = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": input_class, "inputmode": "numeric"}),
    )
    occurrences = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": input_class, "inputmode": "numeric", "placeholder": "Leave blank to use End date"}
        ),
        help_text="How many times this should repeat. Leave blank to use End date instead.",
    )

    class Meta:
        model = RecurringRule
        fields = [
            "kind",
            "pocket",
            "category",
            "amount",
            "frequency",
            "interval",
            "start_date",
            "end_date",
            "occurrences",
            "notes",
        ]
        widgets = {
            "kind": forms.Select(attrs={"class": input_class}),
            "pocket": forms.Select(attrs={"class": input_class}),
            "category": forms.Select(attrs={"class": input_class}),
            "frequency": forms.Select(attrs={"class": input_class}),
            "start_date": forms.DateInput(attrs={"class": input_class, "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": input_class, "type": "date"}),
            "notes": forms.TextInput(
                attrs={"class": input_class, "placeholder": "Optional"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get("start_date"):
            self.initial["start_date"] = date.today().isoformat()
        if user is not None:
            self.fields["pocket"].queryset = _manageable_pockets(user)
            self.fields["category"].queryset = Category.objects.for_user(user).active()

    def clean(self):
        cleaned = super().clean()
        end_date = cleaned.get("end_date")
        occurrences = cleaned.get("occurrences")
        if not end_date and not occurrences:
            raise forms.ValidationError(
                "Set an end date or a number of occurrences so the schedule has a stopping point."
            )
        start = cleaned.get("start_date")
        if start and end_date and end_date < start:
            self.add_error("end_date", "End date must be on or after the start date.")
        kind = cleaned.get("kind")
        category = cleaned.get("category")
        if kind and category and category.kind != kind:
            self.add_error("category", f"Category does not match the {kind} kind.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.created_by_id is None:
            obj.created_by = self.user
        if commit:
            obj.save()
        return obj


class TransactionFilterForm(forms.Form):
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": input_class, "type": "date"}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": input_class, "type": "date"}))
    kind = forms.ChoiceField(
        required=False,
        choices=[("", "All kinds")] + TXN_KIND_CHOICES + [("transfer", "Transfer")],
        widget=forms.Select(attrs={"class": input_class}),
    )
    pocket = forms.ModelChoiceField(
        required=False,
        queryset=Pocket.objects.none(),
        empty_label="All pockets",
        widget=forms.Select(attrs={"class": input_class}),
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.none(),
        empty_label="All categories",
        widget=forms.Select(attrs={"class": input_class}),
    )
    show_planned = forms.BooleanField(
        required=False,
        label="Show planned",
        widget=forms.CheckboxInput(attrs={"class": "w-4 h-4 rounded border-brand-300 text-brand-700 focus:ring-brand-300/40"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            from apps.pockets.permissions import visible_pocket_ids

            self.fields["pocket"].queryset = (
                Pocket.objects.filter(id__in=visible_pocket_ids(user))
                .active()
                .order_by("name")
            )
            self.fields["category"].queryset = Category.objects.for_user(user).active()
