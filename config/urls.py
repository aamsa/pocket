from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("pockets/", include("apps.pockets.urls")),
    path("transactions/", include("apps.transactions.urls")),
    path("reports/", include("apps.reports.urls")),
]
