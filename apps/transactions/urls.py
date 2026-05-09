from django.urls import path

from . import views

app_name = "transactions"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.new, name="new"),
    path("<uuid:txn_id>/edit/", views.edit, name="edit"),
    path("<uuid:txn_id>/delete/", views.delete, name="delete"),
    path("categories/", views.categories_index, name="categories"),
    path("categories/new/", views.category_new, name="category_new"),
    path("categories/<uuid:category_id>/edit/", views.category_edit, name="category_edit"),
    path("recurring/", views.recurring_index, name="recurring_index"),
    path("recurring/new/", views.recurring_new, name="recurring_new"),
    path("recurring/<uuid:rule_id>/edit/", views.recurring_edit, name="recurring_edit"),
    path("recurring/<uuid:rule_id>/delete/", views.recurring_delete, name="recurring_delete"),
    path("recurring/<uuid:rule_id>/toggle/", views.recurring_toggle, name="recurring_toggle"),
]
