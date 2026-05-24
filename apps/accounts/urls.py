from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("settings/profile/", views.profile_view, name="profile"),
    path("users/", views.users_index, name="users"),
    path("users/new/", views.user_new, name="user_new"),
    path("users/<int:user_id>/password/", views.user_set_password, name="user_set_password"),
]
