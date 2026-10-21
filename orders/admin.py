"""Admin for orders.

Staff order management gets its own pages in a later phase; this registration
is just so superusers can look at orders in the Django admin. Orders are
created through checkout, so the fields here are read-only.
"""
from django.contrib import admin

from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "payment_status", "total", "placed_at"]
    list_filter = ["status", "payment_status", "placed_at"]
    search_fields = ["order_number", "user__email"]
    inlines = [OrderItemInline, OrderStatusHistoryInline]

    def has_add_permission(self, request):
        return False
