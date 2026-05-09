from django.urls import path

from . import views

app_name = "pockets"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.new, name="new"),
    path("<uuid:pocket_id>/", views.detail, name="detail"),
    path("<uuid:pocket_id>/edit/", views.edit, name="edit"),
    path("<uuid:pocket_id>/archive/", views.archive, name="archive"),
    path("<uuid:pocket_id>/unarchive/", views.unarchive, name="unarchive"),
]
