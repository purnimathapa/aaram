"""Catalogue URLs."""
from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.catalogue, name="catalogue"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
]
