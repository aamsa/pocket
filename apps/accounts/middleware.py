from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve, reverse


OPEN_URL_NAMES = {
    "accounts:login",
    "accounts:logout",
}

OPEN_URL_PREFIXES = (
    "/static/",
    "/media/",
    "/__debug__/",
)


class LoginRequiredMiddleware:
    """Require login for every URL except a small allow-list."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        if any(request.path.startswith(p) for p in OPEN_URL_PREFIXES):
            return self.get_response(request)

        try:
            match = resolve(request.path_info)
            if match.view_name in OPEN_URL_NAMES:
                return self.get_response(request)
        except Exception:
            pass

        return redirect(f"{reverse(settings.LOGIN_URL)}?next={request.path}")


class ForcePasswordChangeMiddleware:
    """If the user is logged in but flagged for forced password change,
    redirect them to /change-password until they comply."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        try:
            profile = request.user.profile
        except Exception:
            return self.get_response(request)

        if not profile.force_password_change:
            return self.get_response(request)

        # Allow logout and the change-password page itself.
        try:
            match = resolve(request.path_info)
            if match.view_name in {"accounts:change_password", "accounts:logout"}:
                return self.get_response(request)
        except Exception:
            pass

        if any(request.path.startswith(p) for p in OPEN_URL_PREFIXES):
            return self.get_response(request)

        return redirect(reverse("accounts:change_password"))
