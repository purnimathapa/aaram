"""Admin registration for core models."""
from django.contrib import admin

from .models import Province, StoreSettings


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "delivery_charge",
        "est_days_min",
        "est_days_max",
        "is_serviceable",
    ]
    list_editable = ["delivery_charge", "is_serviceable"]


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "low_stock_threshold", "max_qty_per_line"]

    def has_add_permission(self, request):
        # Only ever one settings row; edit it instead of adding more.
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
