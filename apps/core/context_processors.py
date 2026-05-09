import os

from django.conf import settings


def _compute_static_version():
    """Cache-bust query value for /static/ URLs. Uses the latest mtime of
    app.js and output.css so any change to either invalidates browser caches
    on the next request. Cheap (two stat calls)."""
    paths = [
        settings.BASE_DIR / "static" / "js" / "app.js",
        settings.BASE_DIR / "static" / "css" / "output.css",
    ]
    try:
        return str(int(max(os.path.getmtime(p) for p in paths if os.path.exists(p))))
    except (ValueError, OSError):
        return "0"


def app_meta(request):
    ctx = {
        "APP_NAME": "Pocket",
        "APP_TAGLINE": "Mindful money for two",
        "GLOBAL_PENDING_INVITES": 0,
        "STATIC_VERSION": _compute_static_version(),
    }
    if request.user.is_authenticated:
        from apps.pockets.models import SHARE_STATUS_PENDING, PocketShare

        ctx["GLOBAL_PENDING_INVITES"] = PocketShare.objects.filter(
            shared_with=request.user, status=SHARE_STATUS_PENDING
        ).count()
    return ctx
