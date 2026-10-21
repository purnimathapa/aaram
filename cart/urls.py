"""Cart URLs."""
from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="detail"),
    path("add/", views.add, name="add"),
    path("<int:pk>/update/", views.update, name="update"),
    path("<int:pk>/remove/", views.remove, name="remove"),
]
