"""Catalogue models: Category, Size, Product, ProductImage, ProductVariant.

Price and stock live on ProductVariant (a size and thickness of a product), so
the catalogue can show the exact price and stock for each option. Products are
deactivated rather than deleted once they have been ordered.
"""
from django.db import models


class Category(models.Model):
    """A mattress type, such as Memory foam or Orthopedic."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    # Short line shown under the category on the home "shop by feel" cards.
    tagline = models.CharField(max_length=160, blank=True)
    # Colours for the CSS layer illustration, so each type looks a little
    # different without needing a photo. Hex values like "#C9B28A".
    comfort_color = models.CharField(max_length=7, default="#E3D3B8")
    core_color = models.CharField(max_length=7, default="#C9B28A")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Size(models.Model):
    """A bed size with its dimensions in inches."""

    name = models.CharField(max_length=30, unique=True)
    length_in = models.PositiveSmallIntegerField()
    width_in = models.PositiveSmallIntegerField()
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(length_in__gt=0) & models.Q(width_in__gt=0),
                name="size_dimensions_positive",
            ),
        ]

    def __str__(self):
        return self.name


class Firmness(models.IntegerChoices):
    """Firmness on a 1 (soft) to 5 (firm) scale, with plain labels."""

    SOFT = 1, "Soft"
    MEDIUM_SOFT = 2, "Medium-soft"
    MEDIUM = 3, "Medium"
    MEDIUM_FIRM = 4, "Medium-firm"
    FIRM = 5, "Firm"


class Product(models.Model):
    """A mattress model. Its sizes and thicknesses are the variants."""

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField()
    material = models.CharField(max_length=160)
    firmness = models.PositiveSmallIntegerField(choices=Firmness.choices)
    warranty_months = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(firmness__gte=1) & models.Q(firmness__lte=5),
                name="product_firmness_between_1_and_5",
            ),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("catalog:product_detail", args=[self.slug])

    @property
    def active_variants(self):
        """Active variants, using the prefetched list when there is one."""
        return [v for v in self.variants.all() if v.is_active]

    @property
    def size_count(self):
        """How many different sizes this product is sold in."""
        return len({v.size_id for v in self.active_variants})

    @property
    def card_stock(self):
        """A coarse stock label for the product card (not per size)."""
        total = sum(v.stock_qty for v in self.active_variants)
        if total == 0:
            return {"text": "Out of stock", "modifier": "bad"}
        if total <= 3:
            return {"text": "Few left", "modifier": "warn"}
        return {"text": "In stock", "modifier": "ok"}


class ProductImage(models.Model):
    """A photo of a product. The layer illustration is used when none exist."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=160)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            # At most one primary image per product.
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_product",
            ),
        ]

    def __str__(self):
        return self.alt_text


class ProductVariant(models.Model):
    """A buyable size and thickness of a product, with its own price and stock."""

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="variants"
    )
    size = models.ForeignKey(Size, on_delete=models.PROTECT, related_name="variants")
    thickness_in = models.PositiveSmallIntegerField()
    sku = models.CharField(max_length=40, unique=True)
    # Money is a decimal, never a float. Price is in NPR.
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["size__sort_order", "thickness_in"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=0),
                name="variant_price_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_qty__gte=0),
                name="variant_stock_non_negative",
            ),
            models.UniqueConstraint(
                fields=["product", "size", "thickness_in"],
                name="unique_variant_per_product_size_thickness",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size.name} {self.thickness_in} in"
