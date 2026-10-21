"""Checkout and order URLs."""
from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/place/", views.place, name="place"),
    path("orders/", views.order_list, name="list"),
    path("orders/<str:number>/", views.order_detail, name="detail"),
    path("orders/<str:number>/cancel/", views.cancel, name="cancel"),
    path(
        "orders/<str:number>/confirmation/",
        views.confirmation,
        name="confirmation",
    ),
]
