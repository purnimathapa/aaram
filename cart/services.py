"""Cart business rules.

Views stay thin and call these functions. Each one validates the request
against the variant's stock and the store's per-line maximum, so the rules
live in one place and are covered by tests.
"""
from core.models import StoreSettings

from .models import CartItem


class CartError(Exception):
    """A cart action the rules do not allow (bad stock, over the limit, ...)."""


def _max_per_line():
    return StoreSettings.load().max_qty_per_line


def add_to_cart(user, variant, quantity):
    """Add a quantity of a variant to the user's cart.

    If the variant is already in the cart, the quantities are merged. The
    result may not exceed the variant's stock or the per-line maximum.
    """
    if quantity < 1:
        raise CartError("Choose a quantity of at least one.")
    if not variant.is_active:
        raise CartError("This size is no longer available.")

    existing = CartItem.objects.filter(user=user, variant=variant).first()
    current = existing.quantity if existing else 0
    wanted = current + quantity

    limit = min(variant.stock_qty, _max_per_line())
    if variant.stock_qty <= 0:
        raise CartError("This size is out of stock.")
    if wanted > limit:
        raise CartError(
            f"You can have at most {limit} of this size in your cart."
        )

    if existing:
        existing.quantity = wanted
        existing.save(update_fields=["quantity"])
        return existing
    return CartItem.objects.create(user=user, variant=variant, quantity=quantity)


def update_quantity(item, quantity):
    """Set a cart line to an exact quantity, within stock and the limit."""
    if quantity < 1:
        raise CartError("Choose a quantity of at least one.")
    limit = min(item.variant.stock_qty, _max_per_line())
    if quantity > limit:
        raise CartError(
            f"Only {limit} of this size can be in your cart."
        )
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def remove_item(item):
    """Remove a line from the cart."""
    item.delete()


def cart_lines(user):
    """Return the user's cart lines with their variants loaded for display."""
    return (
        CartItem.objects.filter(user=user)
        .select_related("variant", "variant__product", "variant__size")
    )
