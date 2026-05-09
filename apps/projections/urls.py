from django.urls import path

from . import views

app_name = "projections"

urlpatterns = [
    path("", views.index, name="index"),
]
