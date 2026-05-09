from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.pockets.models import Pocket
from apps.pockets.permissions import visible_pocket_ids

from .services import (
    HORIZON_CHOICES,
    active_recurring_summary,
    forecast_balance_trajectory,
    monthly_net_forecast,
    resolve_horizon,
    scope_pocket_ids,
)


@login_required
def index(request):
    try:
        horizon_months = int(request.GET.get("horizon") or 6)
    except ValueError:
        horizon_months = 6
    horizon = resolve_horizon(horizon_months)

    pocket_id = request.GET.get("pocket") or None
    pocket_ids = scope_pocket_ids(request.user, pocket_id)

    visible_pockets = (
        Pocket.objects.filter(pk__in=visible_pocket_ids(request.user))
        .select_related("owner", "owner__profile")
        .order_by("name")
    )

    ctx = {
        "horizon": horizon,
        "horizon_choices": HORIZON_CHOICES,
        "pocket_id": pocket_id,
        "visible_pockets": visible_pockets,
        "balance_trajectory": forecast_balance_trajectory(request.user, pocket_ids, horizon),
        "monthly_net": monthly_net_forecast(request.user, pocket_ids, horizon),
        "rules_summary": active_recurring_summary(request.user, pocket_ids),
    }
    template = (
        "projections/_panels.html"
        if request.headers.get("HX-Request")
        else "projections/index.html"
    )
    return render(request, template, ctx)
