from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.reports.services import (
    Period,
    pocket_balances_over_time,
    spending_by_category,
)
from apps.transactions.models import Transaction, Transfer

from .forms import PocketForm, ShareInviteForm
from .models import (
    POCKET_KIND_CREDIT,
    SHARE_STATUS_ACCEPTED,
    SHARE_STATUS_DECLINED,
    SHARE_STATUS_PENDING,
    SHARE_STATUS_REVOKED,
    Pocket,
    PocketShare,
)
from .permissions import can_manage, can_view, require_pocket_permission
from .services import (
    active_installment_plans,
    balance_for,
    card_cycle,
    shared_pocket_groups,
    user_pocket_tree,
)

POCKET_RECENT_LIMIT = 10
POCKET_DETAIL_RANGES = (7, 14, 30)
POCKET_DETAIL_DEFAULT_RANGE = 30


def _card_row(pocket, *, permission=None):
    return {
        "pocket": pocket,
        "permission": permission,
        "balance": balance_for(pocket),
        "cycle": card_cycle(pocket),
    }


@login_required
def index(request):
    cash_rows = []
    card_rows = []
    for p, depth in user_pocket_tree(request.user):
        if p.kind == POCKET_KIND_CREDIT:
            card_rows.append(_card_row(p))
        else:
            cash_rows.append(
                {
                    "pocket": p,
                    "depth": depth,
                    "balance": balance_for(p, include_descendants=True),
                }
            )

    shared_cash_groups = []
    shared_card_groups = []
    for group in shared_pocket_groups(request.user):
        cash = []
        cards = []
        for p, depth, permission in group["rows"]:
            if p.kind == POCKET_KIND_CREDIT:
                cards.append(_card_row(p, permission=permission))
            else:
                cash.append(
                    {
                        "pocket": p,
                        "depth": depth,
                        "permission": permission,
                        "balance": balance_for(p, include_descendants=True),
                    }
                )
        if cash:
            shared_cash_groups.append({"owner": group["owner"], "rows": cash})
        if cards:
            shared_card_groups.append({"owner": group["owner"], "rows": cards})

    pending_count = PocketShare.objects.filter(
        shared_with=request.user, status=SHARE_STATUS_PENDING
    ).count()
    return render(
        request,
        "pockets/index.html",
        {
            "rows": cash_rows,
            "card_rows": card_rows,
            "shared_groups": shared_cash_groups,
            "shared_card_groups": shared_card_groups,
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
    try:
        days = int(request.GET.get("range", POCKET_DETAIL_DEFAULT_RANGE))
    except (TypeError, ValueError):
        days = POCKET_DETAIL_DEFAULT_RANGE
    if days not in POCKET_DETAIL_RANGES:
        days = POCKET_DETAIL_DEFAULT_RANGE

    today = date.today()
    period = Period(today - timedelta(days=days - 1), today, f"Last {days} days", "day")
    pocket_ids = pocket.descendant_ids_with_self()
    series_name = f"{pocket.name} (downstream)" if len(pocket_ids) > 1 else pocket.name

    balance_chart = pocket_balances_over_time(
        request.user, period, pocket_ids, series_name=series_name
    )
    spending_chart = spending_by_category(request.user, period, pocket_ids)

    if request.headers.get("HX-Request"):
        return render(
            request,
            "pockets/_detail_charts.html",
            {
                "pocket": pocket,
                "range_days": days,
                "range_choices": POCKET_DETAIL_RANGES,
                "balance_chart": balance_chart,
                "spending_chart": spending_chart,
            },
        )

    is_credit = pocket.kind == POCKET_KIND_CREDIT
    cycle = card_cycle(pocket) if is_credit else None
    plans = active_installment_plans(pocket) if is_credit else []
    children = [] if is_credit else list(pocket.children.all().active())
    own_balance = balance_for(pocket, include_descendants=False)
    downstream_balance = (
        None if is_credit else balance_for(pocket, include_descendants=True)
    )

    txn_qs = (
        Transaction.objects.filter(pocket=pocket)
        .select_related("pocket", "category", "created_by")
        .order_by("-occurred_on", "-created_at")
    )
    transfer_qs = (
        Transfer.objects.filter(Q(from_pocket=pocket) | Q(to_pocket=pocket))
        .select_related("from_pocket", "to_pocket", "created_by")
        .order_by("-occurred_on", "-created_at")
    )
    rows = []
    for t in txn_qs[: POCKET_RECENT_LIMIT * 2]:
        rows.append({"type": "txn", "occurred_on": t.occurred_on, "obj": t})
    for tr in transfer_qs[: POCKET_RECENT_LIMIT * 2]:
        rows.append({"type": "transfer", "occurred_on": tr.occurred_on, "obj": tr})
    rows.sort(
        key=lambda r: (r["occurred_on"], getattr(r["obj"], "created_at", None)),
        reverse=True,
    )
    rows = rows[:POCKET_RECENT_LIMIT]

    return render(
        request,
        "pockets/detail.html",
        {
            "pocket": pocket,
            "is_credit": is_credit,
            "cycle": cycle,
            "plans": plans,
            "children": children,
            "own_balance": own_balance,
            "downstream_balance": downstream_balance,
            "ancestors": list(pocket.ancestors())[::-1],  # root first
            "rows": rows,
            "range_days": days,
            "range_choices": POCKET_DETAIL_RANGES,
            "balance_chart": balance_chart,
            "spending_chart": spending_chart,
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
