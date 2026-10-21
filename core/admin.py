"""Admin registration for core models."""
from django.contrib import admin

from .models import Province


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
