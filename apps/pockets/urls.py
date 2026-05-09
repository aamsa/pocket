from django.urls import path

from . import views

app_name = "pockets"

urlpatterns = [
    path("", views.index, name="index"),
]
