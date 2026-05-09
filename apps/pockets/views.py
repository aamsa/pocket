from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import PocketForm
from .models import Pocket
from .permissions import require_pocket_permission
from .services import balance_for, user_pocket_tree


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
    return render(request, "pockets/index.html", {"rows": enriched})


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
