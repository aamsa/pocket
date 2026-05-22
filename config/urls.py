from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("transactions/", include("apps.transactions.urls")),
    path("ledger/", include("apps.ledger.urls")),
    path("reports/", include("apps.reports.urls")),
]
