"""Review rules: who may review a product.

A customer may review a mattress only if one of their orders that contains it
has been Delivered, and they have not already reviewed it. Keeping this in one
function means the product page and the submit view agree on the rule.
"""
from orders.models import OrderStatus

from .models import Review


def has_reviewed(user, product):
    """True if this user has already reviewed this product."""
    return Review.objects.filter(user=user, product=product).exists()


def has_delivered_order(user, product):
    """True if the user has a Delivered order that included this product."""
    return user.orders.filter(
        status=OrderStatus.DELIVERED,
        items__variant__product=product,
    ).exists()


def can_review(user, product):
    """True if the user is allowed to leave a review for this product now."""
    if not user.is_authenticated:
        return False
    return has_delivered_order(user, product) and not has_reviewed(user, product)
