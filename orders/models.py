"""Order models.

An Order is a placed cash-on-delivery order. To keep the record correct even
if a product, its price or the customer's address changes later, the order and
its items store *snapshots* of everything at the moment of ordering:

- OrderItem copies the product name, size label, SKU and the unit price.
- Order copies the delivery address fields.

OrderStatusHistory records every status change, so the customer and staff can
see exactly when the order moved from one step to the next.
"""
from django.conf import settings
from django.db import models


class OrderStatus(models.TextChoices):
    """The steps an order moves through. Cancelled can end it early."""

    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class PaymentMethod(models.TextChoices):
    COD = "cod", "Cash on Delivery"
    KHALTI = "khalti", "Khalti"


class PaymentStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PAID = "paid", "Paid"


class Order(models.Model):
    """One placed order, with its totals and a snapshot of the address."""

    # Human-readable number like AR-2026-00042. It is assigned right after the
    # order is saved (see orders/services.place_order), built from the year and
    # the order's id, so it is always unique and easy to read out over the phone.
    order_number = models.CharField(
        max_length=20, unique=True, null=True, editable=False
    )
    # PROTECT: never delete a customer who has orders, so sales records survive.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=12, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )

    # Snapshot of the delivery address (copied so later edits do not change it).
    recipient = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    province_name = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    municipality = models.CharField(max_length=100)
    ward_no = models.PositiveSmallIntegerField()
    street_tole = models.CharField(max_length=150)
    landmark = models.CharField(max_length=150, blank=True)
    delivery_note = models.CharField(max_length=300, blank=True)

    # Money is always a Decimal, never a float. Amounts are in NPR.
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    placed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-placed_at"]
        constraints = [
            # The total must always equal subtotal + delivery, at the database
            # level, so a wrong total can never be saved.
            models.CheckConstraint(
                condition=models.Q(
                    total=models.F("subtotal") + models.F("delivery_charge")
                ),
                name="order_total_is_subtotal_plus_delivery",
            ),
        ]

    def __str__(self):
        return self.order_number or f"Order {self.pk}"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("orders:detail", args=[self.order_number])

    @property
    def can_customer_cancel(self):
        """A customer may cancel only while the order is still Pending."""
        return self.status == OrderStatus.PENDING


class OrderItem(models.Model):
    """One line of an order: a snapshot of a variant and how many were bought."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    # Kept for reference, but nullable: if the variant is ever removed the order
    # line stays intact because the details below are copied, not looked up.
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    # Snapshots taken when the order was placed.
    product_name = models.CharField(max_length=200)
    variant_label = models.CharField(max_length=200)
    sku = models.CharField(max_length=40)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="order_item_quantity_at_least_one",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    line_total=models.F("unit_price") * models.F("quantity")
                ),
                name="order_item_line_total_matches",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_name} ({self.variant_label})"


class OrderStatusHistory(models.Model):
    """One row for each status change, for the order's timeline."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="history"
    )
    # Blank on the first row (the order being placed has no previous status).
    from_status = models.CharField(
        max_length=12, choices=OrderStatus.choices, blank=True
    )
    to_status = models.CharField(max_length=12, choices=OrderStatus.choices)
    # Who made the change (null if the system did it); kept if the user is gone.
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_changes",
    )
    note = models.CharField(max_length=300, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.order}: {self.from_status or 'new'} -> {self.to_status}"
