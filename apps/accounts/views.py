from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from django.contrib import messages

from .decorators import superuser_required
from .forms import (
    AdminUserCreateForm,
    BrandedPasswordChangeForm,
    BrandedSetPasswordForm,
    LoginForm,
    ProfileForm,
)


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        next_url = request.GET.get("next") or request.POST.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        if form.user.profile.force_password_change:
            return redirect("accounts:change_password")
        return redirect("core:dashboard")

    return render(request, "auth/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
@require_http_methods(["GET", "POST"])
def change_password_view(request):
    form = BrandedPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        profile = user.profile
        profile.force_password_change = False
        profile.save(update_fields=["force_password_change"])
        return redirect("core:dashboard")
    return render(request, "auth/change_password.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    form = ProfileForm(request.POST or None, profile=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "settings/profile.html", {"form": form})


# --- Superadmin: user management --------------------------------------------


@login_required
@superuser_required
def users_index(request):
    from apps.ledger.services import user_household

    users = get_user_model().objects.select_related("profile").order_by("username")
    rows = [{"u": u, "household": user_household(u)} for u in users]
    return render(request, "accounts/users/index.html", {"rows": rows})


@login_required
@superuser_required
@require_http_methods(["GET", "POST"])
def user_new(request):
    form = AdminUserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(
            request,
            f"User '{user.username}' created. They'll be asked to set their own password on first login.",
        )
        return redirect("accounts:users")
    return render(request, "accounts/users/form.html", {"form": form, "mode": "new"})


@login_required
@superuser_required
@require_http_methods(["GET", "POST"])
def user_set_password(request, user_id):
    target = get_object_or_404(get_user_model(), pk=user_id)
    form = BrandedSetPasswordForm(target, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        profile = target.profile
        profile.force_password_change = True
        profile.save(update_fields=["force_password_change"])
        messages.success(
            request,
            f"Password reset for '{target.username}'. They'll be asked to change it on next login.",
        )
        return redirect("accounts:users")
    return render(
        request,
        "accounts/users/form.html",
        {"form": form, "mode": "password", "target": target},
    )
