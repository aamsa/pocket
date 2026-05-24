from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (
    CategoryForm,
    TransactionFilterForm,
    TransactionForm,
)
from .models import Category, Transaction


PAGE_SIZE = 50


@login_required
def index(request):
    from apps.ledger.services import household_user_ids

    form = TransactionFilterForm(request.GET or None, user=request.user)
    cleaned = form.cleaned_data if form.is_valid() else {}

    person = cleaned.get("person") or "me"
    owner_ids = household_user_ids(request.user) if person == "household" else [request.user.id]

    qs = Transaction.objects.filter(owner_id__in=owner_ids).select_related(
        "category", "owner", "owner__profile", "recurring_rule"
    )
    if cleaned.get("start"):
        qs = qs.filter(occurred_on__gte=cleaned["start"])
    if cleaned.get("end"):
        qs = qs.filter(occurred_on__lte=cleaned["end"])
    if cleaned.get("kind"):
        qs = qs.filter(kind=cleaned["kind"])
    if cleaned.get("category"):
        qs = qs.filter(category=cleaned["category"])

    paginator = Paginator(qs.order_by("-occurred_on", "-created_at"), PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    # Carry the active filters (minus `page`) onto the "Load older" button.
    params = request.GET.copy()
    params.pop("page", None)
    filter_query = params.urlencode()

    # Count active filters for the mobile "Filters" disclosure badge.
    filter_count = sum(1 for k in ("start", "end", "kind", "category") if cleaned.get(k))
    if person != "me":
        filter_count += 1

    # A just-deleted transaction (?undo=<id>) offers a one-tap restore banner.
    undo_txn = None
    undo_id = request.GET.get("undo")
    if undo_id:
        try:
            undo_txn = (
                Transaction.all_objects.filter(
                    pk=undo_id, owner=request.user, archived_at__isnull=False
                )
                .select_related("category")
                .first()
            )
        except (ValueError, ValidationError):
            undo_txn = None

    ctx = {
        "form": form,
        "page_obj": page_obj,
        "txns": page_obj.object_list,
        "filter_query": filter_query,
        "filter_count": filter_count,
        "undo_txn": undo_txn,
    }
    if request.headers.get("HX-Request"):
        # A `page` param means the "Load older" button (append rows); the filter
        # form never sends one, so it always lands on the full list partial.
        template = "transactions/_rows.html" if request.GET.get("page") else "transactions/_list.html"
    else:
        template = "transactions/index.html"
    return render(request, template, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def new(request):
    kind = request.GET.get("kind") or request.POST.get("kind") or "expense"
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user, kind=kind)
        if form.is_valid():
            txn = form.save()
            amount = f"{txn.amount:,.0f}".replace(",", ".")
            messages.success(request, f"{txn.get_kind_display()} of Rp {amount} saved.")
            return redirect("transactions:index")
    else:
        form = TransactionForm(user=request.user, kind=kind)
    return render(
        request,
        "transactions/form.html",
        {"form": form, "mode": "new", "kind": kind},
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, txn_id):
    txn = get_object_or_404(Transaction, pk=txn_id, owner=request.user)
    if request.method == "POST":
        form = TransactionForm(request.POST, instance=txn, user=request.user, kind=txn.kind)
        if form.is_valid():
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
    txn = get_object_or_404(Transaction, pk=txn_id, owner=request.user)
    # Soft delete so it can be undone; hidden everywhere by the default manager.
    txn.archived_at = timezone.now()
    txn.save(update_fields=["archived_at"])
    messages.success(request, "Transaction deleted.")
    return redirect(f"{reverse('transactions:index')}?undo={txn.id}")


@login_required
@require_http_methods(["POST"])
def undo_delete(request, txn_id):
    Transaction.all_objects.filter(
        pk=txn_id, owner=request.user, archived_at__isnull=False
    ).update(archived_at=None)
    messages.success(request, "Transaction restored.")
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
