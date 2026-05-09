from django.urls import path

from . import views

app_name = "pockets"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.new, name="new"),
    path("inbox/", views.shares_inbox, name="shares_inbox"),
    path("<uuid:pocket_id>/", views.detail, name="detail"),
    path("<uuid:pocket_id>/edit/", views.edit, name="edit"),
    path("<uuid:pocket_id>/archive/", views.archive, name="archive"),
    path("<uuid:pocket_id>/unarchive/", views.unarchive, name="unarchive"),
    path("<uuid:pocket_id>/share/", views.share, name="share"),
    path("shares/<uuid:share_id>/revoke/", views.share_revoke, name="share_revoke"),
    path("shares/<uuid:share_id>/<str:action>/", views.share_respond, name="share_respond"),
]
