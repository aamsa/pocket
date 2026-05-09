"""Permission helpers. Sharing across users arrives in Phase 6 — for now
only the owner can view or manage their own pockets."""

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Pocket


def can_view(user, pocket) -> bool:
    if not user.is_authenticated:
        return False
    if pocket.owner_id == user.id:
        return True
    # PocketShare-based access lands in Phase 6.
    return False


def can_manage(user, pocket) -> bool:
    if not user.is_authenticated:
        return False
    if pocket.owner_id == user.id:
        return True
    return False


def require_pocket_permission(level: str):
    """Decorator: 404/403 a view if the current user can't access the pocket
    identified by `pocket_id` URL kwarg. `level` is 'view' or 'manage'."""

    check = {"view": can_view, "manage": can_manage}[level]

    def decorator(view):
        @wraps(view)
        def wrapper(request, pocket_id, *args, **kwargs):
            pocket = get_object_or_404(Pocket, pk=pocket_id)
            if not check(request.user, pocket):
                raise PermissionDenied
            request.pocket = pocket
            return view(request, pocket, *args, **kwargs)

        return wrapper

    return decorator
