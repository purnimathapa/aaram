"""Admin for the catalogue, with variant and image inlines on products."""
from django.contrib import admin

from .models import Category, Product, ProductImage, ProductVariant, Size


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["name", "length_in", "width_in", "sort_order"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "firmness", "is_active"]
    list_filter = ["category", "is_active", "firmness"]
    search_fields = ["name", "material"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [ProductVariantInline, ProductImageInline]
