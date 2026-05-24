from datetime import date, timedelta

from django import forms

from apps.transactions.models import Category

from .models import CADENCE_WEEKLY, Budget, Goal, RecurringRule
from .services import _clamp_day_to_month, _shift_month


input_class = (
    "w-full rounded-xl bg-brand-50 border border-brand-200 px-4 py-3 "
    "text-brand-900 placeholder-brand-400 focus:border-brand-500 "
    "focus:outline-none focus:ring-2 focus:ring-brand-300/40"
)


def _amount_field(label="Amount"):
    return forms.DecimalField(
        max_digits=14,
        decimal_places=0,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": input_class, "inputmode": "numeric", "placeholder": "0"}
        ),
        label=label,
    )


class BudgetForm(forms.ModelForm):
    limit_amount = _amount_field("Monthly limit")

    class Meta:
        model = Budget
        fields = ["category", "limit_amount"]
        widgets = {"category": forms.Select(attrs={"class": input_class})}

    def __init__(self, *args, user=None, month=None, **kwargs):
        self.user = user
        self.month = month or date.today().replace(day=1)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = (
                Category.objects.for_user(user).active().expense().order_by("name")
            )

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if category and self.user is not None:
            qs = Budget.objects.filter(
                user=self.user, category=category, month=self.month.replace(day=1)
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("category", "You already have a budget for this category this month.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.user = self.user
        obj.month = self.month.replace(day=1)
        if commit:
            obj.save()
        return obj


class GoalForm(forms.ModelForm):
    target_amount = _amount_field("Target amount")

    class Meta:
        model = Goal
        fields = ["name", "target_amount", "current_amount", "target_date"]
        widgets = {
            "name": forms.TextInput(attrs={"class": input_class, "autofocus": True, "placeholder": "e.g. Vacation"}),
            "current_amount": forms.NumberInput(
                attrs={"class": input_class, "inputmode": "numeric", "placeholder": "0"}
            ),
            "target_date": forms.DateInput(attrs={"class": input_class, "type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["current_amount"].required = False
        self.fields["target_date"].required = False

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.user_id is None:
            obj.user = self.user
        if obj.current_amount is None:
            obj.current_amount = 0
        if commit:
            obj.save()
        return obj


class GoalContributeForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=0,
        widget=forms.NumberInput(
            attrs={"class": input_class, "inputmode": "numeric", "placeholder": "0"}
        ),
        label="Add to goal",
        help_text="Use a negative number to subtract.",
    )


class RecurringRuleForm(forms.ModelForm):
    amount = _amount_field()

    class Meta:
        model = RecurringRule
        fields = ["kind", "amount", "category", "notes", "cadence", "anchor_day"]
        widgets = {
            "kind": forms.Select(attrs={"class": input_class}),
            "category": forms.Select(attrs={"class": input_class}),
            "notes": forms.TextInput(attrs={"class": input_class, "placeholder": "Optional"}),
            "cadence": forms.Select(attrs={"class": input_class}),
            "anchor_day": forms.NumberInput(attrs={"class": input_class, "min": 0, "max": 28}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.for_user(user).active()

    def clean(self):
        cleaned = super().clean()
        cadence = cleaned.get("cadence")
        anchor = cleaned.get("anchor_day")
        if anchor is not None:
            if cadence == CADENCE_WEEKLY and not (0 <= anchor <= 6):
                self.add_error("anchor_day", "Weekly: use 0 (Mon) to 6 (Sun).")
            elif cadence != CADENCE_WEEKLY and not (1 <= anchor <= 28):
                self.add_error("anchor_day", "Monthly: use a day from 1 to 28.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.owner_id is None:
            obj.owner = self.user
        if obj._state.adding or not obj.next_run:
            obj.next_run = self._first_run(obj)
        if commit:
            obj.save()
        return obj

    @staticmethod
    def _first_run(rule, after=None):
        today = after or date.today()
        if rule.cadence == CADENCE_WEEKLY:
            delta = (rule.anchor_day - today.weekday()) % 7
            return today + timedelta(days=delta)
        candidate = _clamp_day_to_month(today.year, today.month, rule.anchor_day)
        if candidate >= today:
            return candidate
        year, month = _shift_month(today, 1)
        return _clamp_day_to_month(year, month, rule.anchor_day)
