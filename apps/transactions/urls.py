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
    path("sources/", views.sources_index, name="sources"),
    path("sources/new/", views.source_new, name="source_new"),
    path("sources/<uuid:source_id>/edit/", views.source_edit, name="source_edit"),
    path("sources/<uuid:source_id>/archive/", views.source_archive, name="source_archive"),
]
