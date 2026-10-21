"""Make the cart count available to every template for the header badge."""
from django.db.models import Sum

from .models import CartItem


def cart_count(request):
    """Total quantity of items in the logged-in user's cart (0 if anonymous)."""
    if not request.user.is_authenticated:
        return {"cart_count": 0}
    total = CartItem.objects.filter(user=request.user).aggregate(
        total=Sum("quantity")
    )["total"]
    return {"cart_count": total or 0}
