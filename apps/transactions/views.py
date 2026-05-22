from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import (
    CategoryForm,
    SourceForm,
    TransactionFilterForm,
    TransactionForm,
)
from .models import Category, Source, Transaction


PAGE_SIZE = 50


@login_required
def index(request):
    from apps.ledger.services import household_user_ids

    form = TransactionFilterForm(request.GET or None, user=request.user)
    cleaned = form.cleaned_data if form.is_valid() else {}

    person = cleaned.get("person") or "me"
    owner_ids = household_user_ids(request.user) if person == "household" else [request.user.id]

    qs = Transaction.objects.filter(owner_id__in=owner_ids).select_related(
        "source", "category", "owner", "owner__profile", "recurring_rule"
    )
    if cleaned.get("start"):
        qs = qs.filter(occurred_on__gte=cleaned["start"])
    if cleaned.get("end"):
        qs = qs.filter(occurred_on__lte=cleaned["end"])
    if cleaned.get("kind"):
        qs = qs.filter(kind=cleaned["kind"])
    if cleaned.get("category"):
        qs = qs.filter(category=cleaned["category"])
    if cleaned.get("source"):
        qs = qs.filter(source=cleaned["source"])

    txns = list(qs.order_by("-occurred_on", "-created_at")[:PAGE_SIZE])

    template = "transactions/_list.html" if request.headers.get("HX-Request") else "transactions/index.html"
    return render(request, template, {"form": form, "txns": txns})


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
        initial = {}
        if request.GET.get("source"):
            initial["source"] = request.GET["source"]
        form = TransactionForm(user=request.user, kind=kind, initial=initial)
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


# --- Sources ----------------------------------------------------------------


@login_required
def sources_index(request):
    from apps.ledger.services import user_household

    sources = (
        Source.objects.for_household(user_household(request.user)).active().order_by("name")
    )
    return render(request, "sources/index.html", {"sources": sources})


@login_required
@require_http_methods(["GET", "POST"])
def source_new(request):
    if request.method == "POST":
        form = SourceForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Source created.")
            return redirect("transactions:sources")
    else:
        form = SourceForm(user=request.user)
    return render(request, "sources/form.html", {"form": form, "mode": "new"})


@login_required
@require_http_methods(["GET", "POST"])
def source_edit(request, source_id):
    from apps.ledger.services import user_household

    source = get_object_or_404(Source, pk=source_id)
    if source.household_id != getattr(user_household(request.user), "id", None):
        raise PermissionDenied
    if request.method == "POST":
        form = SourceForm(request.POST, instance=source, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Source updated.")
            return redirect("transactions:sources")
    else:
        form = SourceForm(instance=source, user=request.user)
    return render(
        request,
        "sources/form.html",
        {"form": form, "mode": "edit", "source": source},
    )


@login_required
@require_http_methods(["POST"])
def source_archive(request, source_id):
    from django.utils import timezone

    from apps.ledger.services import user_household

    source = get_object_or_404(Source, pk=source_id)
    if source.household_id != getattr(user_household(request.user), "id", None):
        raise PermissionDenied
    source.archived_at = timezone.now()
    source.save(update_fields=["archived_at", "updated_at"])
    messages.success(request, "Source archived.")
    return redirect("transactions:sources")
