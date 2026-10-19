"""Admin registration for the custom user model."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Manage users in the admin using email as the identifier."""

    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "phone", "is_staff"]
    search_fields = ["email", "first_name", "last_name", "phone"]

    # Rebuild the default fieldsets around email and phone (no username field).
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["recipient", "user", "province", "district", "is_default"]
    list_filter = ["province", "is_default"]
    search_fields = ["recipient", "user__email", "district", "municipality"]
