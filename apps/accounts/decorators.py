from functools import wraps

from django.core.exceptions import PermissionDenied


def superuser_required(view):
    """Allow only superusers. Authenticated non-superusers get a 403; anonymous
    users are handled upstream by LoginRequiredMiddleware / @login_required."""

    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return _wrapped
