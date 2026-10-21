"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("mattresses/", include("catalog.urls")),
    path("cart/", include("cart.urls")),
    path("", include("core.urls")),
]
