"""Cart views.

The cart belongs to the logged-in user, so every view requires login. The
add, update and remove actions change data and are POST only; the cart page
itself is a normal GET. Each action validates through cart.services and shows
a message, then redirects (Post/Redirect/Get) so a refresh does not repeat it.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import ProductVariant
from core.models import StoreSettings

from . import services
from .models import CartItem


@login_required
def cart_detail(request):
    """Show the cart: its lines, any stock warnings, and the subtotal."""
    settings = StoreSettings.load()
    lines = list(services.cart_lines(request.user))

    # Drop lines whose variant was deactivated since it was added.
    inactive = [line for line in lines if not line.variant.is_active]
    if inactive:
        CartItem.objects.filter(pk__in=[line.pk for line in inactive]).delete()
        lines = [line for line in lines if line.variant.is_active]
        messages.warning(
            request,
            "Some items were removed because they are no longer available.",
        )

    rows = []
    subtotal = 0
    for line in lines:
        stock = line.variant.stock_qty
        if line.quantity > stock:
            warning = f"Only {stock} left — reduce the quantity to check out."
        elif 0 < stock <= settings.low_stock_threshold:
            warning = f"Only {stock} left"
        else:
            warning = ""
        # Quantities the dropdown offers: 1 up to the stock-or-limit cap, but
        # never fewer than the line already holds, so the current value shows.
        cap = min(stock, settings.max_qty_per_line)
        choices = list(range(1, max(cap, line.quantity) + 1))
        subtotal += line.line_total
        rows.append({"item": line, "warning": warning, "choices": choices})

    context = {
        "rows": rows,
        "subtotal": subtotal,
        "max_qty_per_line": settings.max_qty_per_line,
    }
    return render(request, "cart/cart.html", context)


@require_POST
@login_required
def add(request):
    """Add the chosen variant and quantity to the cart."""
    variant = get_object_or_404(ProductVariant, pk=request.POST.get("variant"))
    quantity = _parse_quantity(request.POST.get("quantity"), default=1)
    try:
        services.add_to_cart(request.user, variant, quantity)
        messages.success(request, f"Added {variant.product.name} to your cart.")
    except services.CartError as error:
        messages.error(request, str(error))
        return redirect(variant.product.get_absolute_url())
    return redirect("cart:detail")


@require_POST
@login_required
def update(request, pk):
    """Set a cart line to a new quantity."""
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    quantity = _parse_quantity(request.POST.get("quantity"), default=item.quantity)
    try:
        services.update_quantity(item, quantity)
    except services.CartError as error:
        messages.error(request, str(error))
    return redirect("cart:detail")


@require_POST
@login_required
def remove(request, pk):
    """Remove a line from the cart."""
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    services.remove_item(item)
    messages.success(request, "Item removed from your cart.")
    return redirect("cart:detail")


def _parse_quantity(raw, default):
    """Read a quantity from the form; fall back to default if it is not a number."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default
