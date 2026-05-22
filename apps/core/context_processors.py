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
    return {
        "APP_NAME": "Pocket",
        "APP_TAGLINE": "Mindful money for two",
        "STATIC_VERSION": _compute_static_version(),
    }
