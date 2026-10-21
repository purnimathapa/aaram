"""Read-only admin so superusers can inspect payment attempts."""
from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "provider", "status", "amount", "pidx", "created_at"]
    list_filter = ["status", "provider"]
    search_fields = ["order__order_number", "pidx"]

    def has_add_permission(self, request):
        return False
