"""Permission helpers — owner OR accepted PocketShare on the pocket itself
or any ancestor. Sharing a parent pocket implicitly shares its descendants
at the same permission level."""

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import (
    SHARE_PERMISSION_MANAGE,
    SHARE_STATUS_ACCEPTED,
    Pocket,
    PocketShare,
)


def _accepted_share_exists(user, pocket, permission=None):
    chain_ids = pocket.ancestor_ids_with_self()
    qs = PocketShare.objects.filter(
        pocket_id__in=chain_ids,
        shared_with=user,
        status=SHARE_STATUS_ACCEPTED,
    )
    if permission == SHARE_PERMISSION_MANAGE:
        qs = qs.filter(permission=SHARE_PERMISSION_MANAGE)
    return qs.exists()


def can_view(user, pocket) -> bool:
    if not user.is_authenticated:
        return False
    if pocket.owner_id == user.id:
        return True
    return _accepted_share_exists(user, pocket)


def can_manage(user, pocket) -> bool:
    if not user.is_authenticated:
        return False
    if pocket.owner_id == user.id:
        return True
    return _accepted_share_exists(user, pocket, permission=SHARE_PERMISSION_MANAGE)


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


def visible_pocket_ids(user):
    """All pocket ids the user can at least view — used to scope transactions
    feed across owned and shared pockets, including descendants of shared
    parents."""
    owned = list(Pocket.objects.owned_by(user).active().values_list("id", flat=True))

    shared_root_ids = set(
        PocketShare.objects.filter(
            shared_with=user, status=SHARE_STATUS_ACCEPTED
        ).values_list("pocket_id", flat=True)
    )
    if not shared_root_ids:
        return owned

    # Pull every pocket that could be a descendant (small data — fine).
    all_pockets = list(Pocket.objects.active().values("id", "parent_id", "owner_id"))
    by_parent = {}
    by_id = {}
    for p in all_pockets:
        by_parent.setdefault(p["parent_id"], []).append(p["id"])
        by_id[p["id"]] = p

    def collect_subtree(pid):
        out = [pid]
        for child_id in by_parent.get(pid, []):
            out.extend(collect_subtree(child_id))
        return out

    shared_ids = []
    for pid in shared_root_ids:
        if pid in by_id:
            shared_ids.extend(collect_subtree(pid))

    return list({*owned, *shared_ids})
