from datetime import date

from django import forms

from apps.pockets.models import Pocket

from .models import (
    CATEGORY_KIND_INCOME,
    TXN_KIND_CHOICES,
    Category,
    Transaction,
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
            self.fields["pocket"].queryset = Pocket.objects.owned_by(user).active()
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


class TransactionFilterForm(forms.Form):
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": input_class, "type": "date"}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": input_class, "type": "date"}))
    kind = forms.ChoiceField(
        required=False,
        choices=[("", "All kinds")] + TXN_KIND_CHOICES,
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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["pocket"].queryset = Pocket.objects.owned_by(user).active()
            self.fields["category"].queryset = Category.objects.for_user(user).active()
