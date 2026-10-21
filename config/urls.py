"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("mattresses/", include("catalog.urls")),
    path("", include("reviews.urls")),
    path("cart/", include("cart.urls")),
    path("staff/", include("dashboard.urls")),
    path("", include("orders.urls")),
    path("", include("core.urls")),
]

# In development, serve uploaded product images from MEDIA_ROOT.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
