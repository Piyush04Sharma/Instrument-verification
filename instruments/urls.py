from django.urls import path

from . import views

app_name = "instruments"

urlpatterns = [
    path("", views.instrument_list, name="list"),
    path("add/", views.instrument_add, name="add"),
    path("<int:pk>/", views.instrument_detail, name="detail"),
    path("<int:pk>/edit/", views.instrument_edit, name="edit"),
    path("<int:pk>/delete/", views.instrument_delete, name="delete"),
]
