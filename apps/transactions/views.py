from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.pockets.permissions import can_manage, can_view

from .forms import CategoryForm, TransactionFilterForm, TransactionForm
from .models import Category, Transaction


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
    qs = Transaction.objects.for_user(request.user).select_related(
        "pocket", "category", "created_by"
    )
    if form.is_valid():
        if form.cleaned_data.get("start"):
            qs = qs.filter(occurred_on__gte=form.cleaned_data["start"])
        if form.cleaned_data.get("end"):
            qs = qs.filter(occurred_on__lte=form.cleaned_data["end"])
        if form.cleaned_data.get("kind"):
            qs = qs.filter(kind=form.cleaned_data["kind"])
        if form.cleaned_data.get("pocket"):
            qs = qs.filter(pocket=form.cleaned_data["pocket"])
        if form.cleaned_data.get("category"):
            qs = qs.filter(category=form.cleaned_data["category"])

    transactions = list(qs[:PAGE_SIZE])
    template = "transactions/_list.html" if request.headers.get("HX-Request") else "transactions/index.html"
    return render(request, template, {"form": form, "transactions": transactions})


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
