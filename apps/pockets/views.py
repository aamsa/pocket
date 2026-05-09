from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import PocketForm, ShareInviteForm
from .models import (
    SHARE_STATUS_ACCEPTED,
    SHARE_STATUS_DECLINED,
    SHARE_STATUS_PENDING,
    SHARE_STATUS_REVOKED,
    Pocket,
    PocketShare,
)
from .permissions import can_manage, can_view, require_pocket_permission
from .services import balance_for, shared_pocket_groups, user_pocket_tree


@login_required
def index(request):
    rows = user_pocket_tree(request.user)
    enriched = [
        {
            "pocket": p,
            "depth": depth,
            "balance": balance_for(p, include_descendants=True),
        }
        for p, depth in rows
    ]
    shared_groups = []
    for group in shared_pocket_groups(request.user):
        shared_groups.append(
            {
                "owner": group["owner"],
                "rows": [
                    {
                        "pocket": p,
                        "depth": depth,
                        "permission": permission,
                        "balance": balance_for(p, include_descendants=True),
                    }
                    for p, depth, permission in group["rows"]
                ],
            }
        )
    pending_count = PocketShare.objects.filter(
        shared_with=request.user, status=SHARE_STATUS_PENDING
    ).count()
    return render(
        request,
        "pockets/index.html",
        {
            "rows": enriched,
            "shared_groups": shared_groups,
            "pending_invite_count": pending_count,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def new(request):
    if request.method == "POST":
        form = PocketForm(request.POST, user=request.user)
        if form.is_valid():
            pocket = form.save()
            messages.success(request, f"Pocket “{pocket.name}” created.")
            return redirect("pockets:detail", pocket_id=pocket.id)
    else:
        initial = {}
        parent_id = request.GET.get("parent")
        if parent_id:
            parent = Pocket.objects.owned_by(request.user).filter(pk=parent_id).first()
            if parent:
                initial["parent"] = parent
        form = PocketForm(user=request.user, initial=initial)
    return render(request, "pockets/form.html", {"form": form, "mode": "new"})


@login_required
@require_pocket_permission("view")
def detail(request, pocket):
    children = list(pocket.children.all().active())
    own_balance = balance_for(pocket, include_descendants=False)
    downstream_balance = balance_for(pocket, include_descendants=True)
    return render(
        request,
        "pockets/detail.html",
        {
            "pocket": pocket,
            "children": children,
            "own_balance": own_balance,
            "downstream_balance": downstream_balance,
            "ancestors": list(pocket.ancestors())[::-1],  # root first
        },
    )


@login_required
@require_pocket_permission("manage")
@require_http_methods(["GET", "POST"])
def edit(request, pocket):
    if request.method == "POST":
        form = PocketForm(request.POST, instance=pocket, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Pocket “{pocket.name}” updated.")
            return redirect("pockets:detail", pocket_id=pocket.id)
    else:
        form = PocketForm(instance=pocket, user=request.user)
    return render(request, "pockets/form.html", {"form": form, "mode": "edit", "pocket": pocket})


@login_required
@require_pocket_permission("manage")
@require_http_methods(["POST"])
def archive(request, pocket):
    if pocket.is_main:
        messages.error(request, "The Main pocket can't be archived.")
        return redirect("pockets:detail", pocket_id=pocket.id)
    if pocket.children.active().exists():
        messages.error(
            request, "Archive or move sub-pockets first before archiving this one."
        )
        return redirect("pockets:detail", pocket_id=pocket.id)
    pocket.archived_at = timezone.now()
    pocket.save(update_fields=["archived_at", "updated_at"])
    messages.success(request, f"Pocket “{pocket.name}” archived.")
    return redirect("pockets:index")


@login_required
@require_pocket_permission("manage")
@require_http_methods(["POST"])
def unarchive(request, pocket):
    pocket.archived_at = None
    pocket.save(update_fields=["archived_at", "updated_at"])
    messages.success(request, f"Pocket “{pocket.name}” restored.")
    return redirect("pockets:detail", pocket_id=pocket.id)


# --- Sharing ---------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def share(request, pocket_id):
    pocket = get_object_or_404(Pocket, pk=pocket_id)
    # Only the owner can share — sharing of inherited subtrees is not allowed.
    if pocket.owner_id != request.user.id:
        raise PermissionDenied

    if request.method == "POST":
        form = ShareInviteForm(request.POST, pocket=pocket, inviter=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Invite sent to @{form.cleaned_data['username']}.",
            )
            return redirect("pockets:share", pocket_id=pocket.id)
    else:
        form = ShareInviteForm(pocket=pocket, inviter=request.user)

    shares = (
        pocket.shares.exclude(status=SHARE_STATUS_REVOKED)
        .select_related("shared_with", "shared_with__profile", "invited_by")
    )
    return render(
        request,
        "shares/manage.html",
        {"pocket": pocket, "form": form, "shares": shares},
    )


@login_required
@require_http_methods(["POST"])
def share_revoke(request, share_id):
    share = get_object_or_404(PocketShare.objects.select_related("pocket"), pk=share_id)
    if share.pocket.owner_id != request.user.id:
        raise PermissionDenied
    share.status = SHARE_STATUS_REVOKED
    share.responded_at = timezone.now()
    share.save(update_fields=["status", "responded_at"])
    messages.success(request, "Share revoked.")
    return redirect("pockets:share", pocket_id=share.pocket_id)


@login_required
def shares_inbox(request):
    pending = (
        PocketShare.objects.filter(
            shared_with=request.user, status=SHARE_STATUS_PENDING
        )
        .select_related("pocket", "pocket__owner", "pocket__owner__profile", "invited_by")
    )
    history = (
        PocketShare.objects.filter(shared_with=request.user)
        .exclude(status=SHARE_STATUS_PENDING)
        .select_related("pocket", "pocket__owner", "pocket__owner__profile")[:20]
    )
    return render(
        request, "shares/inbox.html", {"pending": pending, "history": history}
    )


@login_required
@require_http_methods(["POST"])
def share_respond(request, share_id, action):
    share = get_object_or_404(PocketShare, pk=share_id, shared_with=request.user)
    if share.status != SHARE_STATUS_PENDING:
        messages.error(request, "This invite has already been answered.")
        return redirect("pockets:shares_inbox")
    if action == "accept":
        share.status = SHARE_STATUS_ACCEPTED
        messages.success(request, f"You can now access “{share.pocket.name}”.")
    elif action == "decline":
        share.status = SHARE_STATUS_DECLINED
        messages.info(request, "Invite declined.")
    else:
        raise PermissionDenied
    share.responded_at = timezone.now()
    share.save(update_fields=["status", "responded_at"])
    return redirect("pockets:shares_inbox")
