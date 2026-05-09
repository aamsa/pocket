from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.pockets.permissions import can_manage, can_view

from .forms import CategoryForm, TransactionFilterForm, TransactionForm, TransferForm
from .models import Category, Transaction, Transfer


PAGE_SIZE = 25


def _ensure_can_manage(user, pocket):
    if not can_manage(user, pocket):
        raise PermissionDenied


def _ensure_can_view(user, pocket):
    if not can_view(user, pocket):
        raise PermissionDenied


@login_required
def index(request):
    form = TransactionFilterForm(request.GET or None, user=request.user)
    cleaned = form.cleaned_data if form.is_valid() else {}

    txn_qs = Transaction.objects.for_user(request.user).select_related(
        "pocket", "category", "created_by"
    )
    transfer_qs = Transfer.objects.filter(
        from_pocket__owner=request.user
    ).select_related("from_pocket", "to_pocket", "created_by")

    if cleaned.get("start"):
        txn_qs = txn_qs.filter(occurred_on__gte=cleaned["start"])
        transfer_qs = transfer_qs.filter(occurred_on__gte=cleaned["start"])
    if cleaned.get("end"):
        txn_qs = txn_qs.filter(occurred_on__lte=cleaned["end"])
        transfer_qs = transfer_qs.filter(occurred_on__lte=cleaned["end"])
    if cleaned.get("pocket"):
        p = cleaned["pocket"]
        txn_qs = txn_qs.filter(pocket=p)
        transfer_qs = transfer_qs.filter(Q(from_pocket=p) | Q(to_pocket=p))
    if cleaned.get("category"):
        txn_qs = txn_qs.filter(category=cleaned["category"])
        transfer_qs = transfer_qs.none()

    kind = cleaned.get("kind")
    if kind == "income" or kind == "expense":
        txn_qs = txn_qs.filter(kind=kind)
        transfer_qs = transfer_qs.none()
    elif kind == "transfer":
        txn_qs = txn_qs.none()

    rows = []
    for t in txn_qs[: PAGE_SIZE * 2]:
        rows.append({"type": "txn", "occurred_on": t.occurred_on, "obj": t})
    for tr in transfer_qs[: PAGE_SIZE * 2]:
        rows.append({"type": "transfer", "occurred_on": tr.occurred_on, "obj": tr})
    rows.sort(key=lambda r: (r["occurred_on"], getattr(r["obj"], "created_at", None)), reverse=True)
    rows = rows[:PAGE_SIZE]

    template = "transactions/_list.html" if request.headers.get("HX-Request") else "transactions/index.html"
    return render(request, template, {"form": form, "rows": rows})


@login_required
@require_http_methods(["GET", "POST"])
def new(request):
    kind = request.GET.get("kind") or request.POST.get("kind") or "expense"
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user, kind=kind)
        if form.is_valid():
            _ensure_can_manage(request.user, form.cleaned_data["pocket"])
            txn = form.save()
            messages.success(
                request,
                f"{txn.get_kind_display()} of {txn.amount:,.0f} saved.".replace(",", "."),
            )
            return redirect("transactions:index")
    else:
        initial = {}
        if request.GET.get("pocket"):
            initial["pocket"] = request.GET["pocket"]
        form = TransactionForm(user=request.user, kind=kind, initial=initial)
    return render(
        request,
        "transactions/form.html",
        {"form": form, "mode": "new", "kind": kind},
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, txn_id):
    txn = get_object_or_404(
        Transaction.objects.select_related("pocket"), pk=txn_id
    )
    _ensure_can_manage(request.user, txn.pocket)
    if request.method == "POST":
        form = TransactionForm(request.POST, instance=txn, user=request.user, kind=txn.kind)
        if form.is_valid():
            _ensure_can_manage(request.user, form.cleaned_data["pocket"])
            form.save()
            messages.success(request, "Transaction updated.")
            return redirect("transactions:index")
    else:
        form = TransactionForm(instance=txn, user=request.user, kind=txn.kind)
    return render(
        request,
        "transactions/form.html",
        {"form": form, "mode": "edit", "kind": txn.kind, "txn": txn},
    )


@login_required
@require_http_methods(["POST"])
def delete(request, txn_id):
    txn = get_object_or_404(Transaction.objects.select_related("pocket"), pk=txn_id)
    _ensure_can_manage(request.user, txn.pocket)
    txn.delete()
    messages.success(request, "Transaction deleted.")
    return redirect("transactions:index")


# --- Transfers --------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def transfer_new(request):
    if request.method == "POST":
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            _ensure_can_manage(request.user, form.cleaned_data["from_pocket"])
            _ensure_can_manage(request.user, form.cleaned_data["to_pocket"])
            form.save()
            messages.success(request, "Transfer recorded.")
            return redirect("transactions:index")
    else:
        initial = {}
        if request.GET.get("from"):
            initial["from_pocket"] = request.GET["from"]
        form = TransferForm(user=request.user, initial=initial)
    return render(request, "transfers/form.html", {"form": form, "mode": "new"})


@login_required
@require_http_methods(["GET", "POST"])
def transfer_edit(request, transfer_id):
    transfer = get_object_or_404(Transfer.objects.select_related("from_pocket", "to_pocket"), pk=transfer_id)
    _ensure_can_manage(request.user, transfer.from_pocket)
    _ensure_can_manage(request.user, transfer.to_pocket)
    if request.method == "POST":
        form = TransferForm(request.POST, instance=transfer, user=request.user)
        if form.is_valid():
            _ensure_can_manage(request.user, form.cleaned_data["from_pocket"])
            _ensure_can_manage(request.user, form.cleaned_data["to_pocket"])
            form.save()
            messages.success(request, "Transfer updated.")
            return redirect("transactions:index")
    else:
        form = TransferForm(instance=transfer, user=request.user)
    return render(
        request,
        "transfers/form.html",
        {"form": form, "mode": "edit", "transfer": transfer},
    )


@login_required
@require_http_methods(["POST"])
def transfer_delete(request, transfer_id):
    transfer = get_object_or_404(Transfer.objects.select_related("from_pocket", "to_pocket"), pk=transfer_id)
    _ensure_can_manage(request.user, transfer.from_pocket)
    _ensure_can_manage(request.user, transfer.to_pocket)
    transfer.delete()
    messages.success(request, "Transfer deleted.")
    return redirect("transactions:index")


# --- Categories -------------------------------------------------------------


@login_required
def categories_index(request):
    income_cats = Category.objects.for_user(request.user).active().income()
    expense_cats = Category.objects.for_user(request.user).active().expense()
    return render(
        request,
        "categories/index.html",
        {"income_cats": income_cats, "expense_cats": expense_cats},
    )


@login_required
@require_http_methods(["GET", "POST"])
def category_new(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created.")
            return redirect("transactions:categories")
    else:
        form = CategoryForm(user=request.user, initial={"kind": request.GET.get("kind", "expense")})
    return render(request, "categories/form.html", {"form": form, "mode": "new"})


@login_required
@require_http_methods(["GET", "POST"])
def category_edit(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    if category.is_default or category.created_by_id != request.user.id:
        raise PermissionDenied
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect("transactions:categories")
    else:
        form = CategoryForm(instance=category, user=request.user)
    return render(
        request,
        "categories/form.html",
        {"form": form, "mode": "edit", "category": category},
    )
