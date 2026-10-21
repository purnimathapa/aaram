"""Cart model.

A CartItem is one variant a logged-in customer means to buy, with a quantity.
The cart lives in the database and is tied to the user, so it survives logging
out and back in and follows the customer between devices.
"""
from django.conf import settings
from django.db import models


class CartItem(models.Model):
    """One line in a customer's cart: a product variant and how many."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveSmallIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at"]
        constraints = [
            # A variant appears at most once per cart; adding it again merges
            # into the existing line instead of creating a duplicate.
            models.UniqueConstraint(
                fields=["user", "variant"],
                name="unique_cart_line_per_user_variant",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="cart_quantity_at_least_one",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.variant} for {self.user}"

    @property
    def line_total(self):
        """Price for this line at the variant's current price."""
        return self.variant.price * self.quantity
