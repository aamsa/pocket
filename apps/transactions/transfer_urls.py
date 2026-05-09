from django.urls import path

from . import views

app_name = "transfers"

urlpatterns = [
    path("new/", views.transfer_new, name="new"),
    path("<uuid:transfer_id>/edit/", views.transfer_edit, name="edit"),
    path("<uuid:transfer_id>/delete/", views.transfer_delete, name="delete"),
]
