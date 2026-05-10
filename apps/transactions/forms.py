import uuid
from datetime import date

from django import forms

from apps.pockets.models import POCKET_KIND_CREDIT, Pocket
from apps.pockets.permissions import can_manage
from apps.pockets.services import _clamp_day_to_month, _shift_month


def _manageable_pockets(user):
    """All active pockets the user can write to: owned + shared with manage."""
    owned = list(Pocket.objects.owned_by(user).active())
    shared = [p for p in Pocket.objects.active() if not p.owner_id == user.id and can_manage(user, p)]
    ids = [p.id for p in owned + shared]
    return Pocket.objects.filter(pk__in=ids).select_related("owner")

from .models import (
    CATEGORY_KIND_INCOME,
    TXN_KIND_CHOICES,
    Category,
    Transaction,
    Transfer,
)


input_class = (
    "w-full rounded-xl bg-brand-50 border border-brand-200 px-4 py-3 "
    "text-brand-900 placeholder-brand-400 focus:border-brand-500 "
    "focus:outline-none focus:ring-2 focus:ring-brand-300/40"
)


INSTALLMENT_CHOICES = [
    (1, "Single payment"),
    (3, "3 months"),
    (6, "6 months"),
    (12, "12 months"),
    (24, "24 months"),
]


class PocketKindSelect(forms.Select):
    """Select widget that tags each <option> with data-kind so Alpine
    can show/hide installment fields depending on the chosen pocket."""

    def __init__(self, *args, kind_lookup=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind_lookup = kind_lookup or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        kind = self.kind_lookup.get(str(value))
        if kind:
            option["attrs"]["data-kind"] = kind
        return option


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
    installment_months = forms.TypedChoiceField(
        coerce=int,
        choices=INSTALLMENT_CHOICES,
        initial=1,
        required=False,
        widget=forms.Select(attrs={"class": input_class}),
        label="Installments",
    )

    class Meta:
        model = Transaction
        fields = ["pocket", "kind", "amount", "category", "occurred_on", "notes"]
        widgets = {
            "pocket": forms.Select(attrs={"class": input_class}),
            "kind": forms.HiddenInput(),
            "category": forms.Select(attrs={"class": input_class}),
            "occurred_on": forms.DateInput(
                attrs={"class": input_class, "type": "date"},
                format="%Y-%m-%d",
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
            pocket_qs = _manageable_pockets(user)
            self.fields["pocket"].queryset = pocket_qs
            kind_lookup = {str(p.id): p.kind for p in pocket_qs}
            self.fields["pocket"].widget = PocketKindSelect(
                attrs={"class": input_class},
                kind_lookup=kind_lookup,
            )
            self.fields["pocket"].widget.choices = self.fields["pocket"].choices
            cat_qs = Category.objects.for_user(user).active()
            if chosen_kind:
                cat_qs = cat_qs.filter(kind=chosen_kind)
            self.fields["category"].queryset = cat_qs

        # Editing an existing row: hide the installment selector. Each child is
        # treated as a normal Transaction once materialised. Use _state.adding
        # (not .pk) because Transaction has a UUID default that populates pk
        # even on unsaved instances.
        if self.instance and not self.instance._state.adding:
            self.fields["installment_months"].widget = forms.HiddenInput()
            self.fields["installment_months"].initial = 1

    def clean(self):
        cleaned = super().clean()
        months = cleaned.get("installment_months") or 1
        if months and months > 1:
            pocket = cleaned.get("pocket")
            kind = cleaned.get("kind") or self.initial.get("kind")
            if not pocket or pocket.kind != POCKET_KIND_CREDIT:
                self.add_error("installment_months", "Installments are only for credit-card pockets.")
            if kind != "expense":
                self.add_error("installment_months", "Installments only apply to expenses.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.created_by_id is None:
            obj.created_by = self.user

        months = int(self.cleaned_data.get("installment_months") or 1)
        is_edit = self.instance and not self.instance._state.adding
        if months <= 1 or is_edit:
            if commit:
                obj.save()
            return obj

        # Materialise N children. Per-month amount uses integer division;
        # the last child eats the remainder so children sum exactly to total.
        total_amount = int(obj.amount)
        base_monthly = total_amount // months
        remainder = total_amount - base_monthly * months
        group_uuid = uuid.uuid4()
        purchase_date = obj.occurred_on

        first_child = None
        for k in range(1, months + 1):
            year, month = _shift_month(purchase_date, k - 1)
            occurred = _clamp_day_to_month(year, month, purchase_date.day)
            amount = base_monthly + (remainder if k == months else 0)
            child = Transaction(
                pocket=obj.pocket,
                kind=obj.kind,
                amount=amount,
                category=obj.category,
                occurred_on=occurred,
                notes=obj.notes,
                created_by=obj.created_by,
                installment_group=group_uuid,
                installment_index=k,
                installment_total=months,
            )
            if commit:
                child.save()
            if first_child is None:
                first_child = child

        return first_child or obj


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
            "occurred_on": forms.DateInput(
                attrs={"class": input_class, "type": "date"}, format="%Y-%m-%d"
            ),
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
        widget=forms.CheckboxInput(
            attrs={"class": "w-4 h-4 rounded border-brand-300 text-brand-700 focus:ring-brand-300/40"}
        ),
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
