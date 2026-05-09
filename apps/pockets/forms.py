from django import forms

from .models import POCKET_COLOR_CHOICES, POCKET_ICON_CHOICES, Pocket


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
