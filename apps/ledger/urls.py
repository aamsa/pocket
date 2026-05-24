from django.urls import path

from . import views

app_name = "ledger"

urlpatterns = [
    # Budgets
    path("budgets/", views.budgets_index, name="budgets"),
    path("budgets/new/", views.budget_new, name="budget_new"),
    path("budgets/<uuid:budget_id>/edit/", views.budget_edit, name="budget_edit"),
    path("budgets/<uuid:budget_id>/delete/", views.budget_delete, name="budget_delete"),
    # Goals
    path("goals/", views.goals_index, name="goals"),
    path("goals/new/", views.goal_new, name="goal_new"),
    path("goals/<uuid:goal_id>/edit/", views.goal_edit, name="goal_edit"),
    path("goals/<uuid:goal_id>/contribute/", views.goal_contribute, name="goal_contribute"),
    path("goals/<uuid:goal_id>/delete/", views.goal_delete, name="goal_delete"),
    # Recurring
    path("recurring/", views.recurring_index, name="recurring"),
    path("recurring/new/", views.recurring_new, name="recurring_new"),
    path("recurring/<uuid:rule_id>/edit/", views.recurring_edit, name="recurring_edit"),
    path("recurring/<uuid:rule_id>/toggle/", views.recurring_toggle, name="recurring_toggle"),
    path("recurring/<uuid:rule_id>/delete/", views.recurring_delete, name="recurring_delete"),
    # Manage My Family
    path("family/", views.family_index, name="family"),
    path("family/add/", views.family_add_member, name="family_add_member"),
    path("family/<uuid:member_id>/remove/", views.family_remove_member, name="family_remove_member"),
    path("family/rename/", views.family_rename, name="family_rename"),
]
