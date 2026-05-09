from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import BrandedPasswordChangeForm, LoginForm


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
def profile_view(request):
    return render(request, "settings/profile.html")
