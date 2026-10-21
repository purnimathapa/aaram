"""Staff dashboard URLs (all under /staff/)."""
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),

    path("orders/", views.order_list, name="order_list"),
    path("orders/<str:number>/", views.order_detail, name="order_detail"),
    path("orders/<str:number>/status/", views.order_status, name="order_status"),

    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_form, name="product_new"),
    path("products/<int:pk>/edit/", views.product_form, name="product_edit"),

    path("inventory/", views.inventory, name="inventory"),
    path("inventory/<int:pk>/adjust/", views.inventory_adjust, name="inventory_adjust"),

    path("customers/", views.customer_list, name="customer_list"),
]
