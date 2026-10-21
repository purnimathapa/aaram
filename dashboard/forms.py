"""Forms for the staff product editor.

A product is edited together with its variants (size, price, stock) and its
images, using Django inline formsets so one page saves all three. Variants are
deactivated with their is_active flag rather than deleted, so an order that
refers to them stays intact; images can be deleted outright.
"""
from django import forms
from django.forms import inlineformset_factory

from catalog.models import Product, ProductImage, ProductVariant


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "category", "name", "slug", "description",
            "material", "firmness", "warranty_months", "is_active",
        ]


# One formset for the product's variants. extra=1 shows a blank row to add one.
VariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    fields=["size", "thickness_in", "sku", "price", "stock_qty", "is_active"],
    extra=1,
    can_delete=False,
)

# One formset for the product's images; these may be deleted.
ImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=["image", "alt_text", "sort_order", "is_primary"],
    extra=1,
    can_delete=True,
)
