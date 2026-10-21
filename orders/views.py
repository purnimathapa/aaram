"""Order views: checkout, placing an order, order history and detail.

All of these need a logged-in customer, and a customer only ever sees their
own orders (every lookup filters by request.user, so another person's order
number returns 404).
"""
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Address
from cart.services import cart_lines

from . import services
from .models import Order, OrderStatus, PaymentMethod


# The normal forward steps, in order, with the words shown on the timeline.
TIMELINE_STEPS = [
    (OrderStatus.PENDING, "Order placed", "We received your order and reserved your mattress."),
    (OrderStatus.CONFIRMED, "Confirmed", "Confirmed with you by phone."),
    (OrderStatus.PROCESSING, "Processing", "Your mattress is being packed for dispatch."),
    (OrderStatus.SHIPPED, "Shipped", "Handed to the delivery person."),
    (OrderStatus.DELIVERED, "Delivered", "Pay in cash and enjoy your new mattress."),
]


@login_required
def checkout(request):
    """Show the checkout page: address choice, order summary and the totals."""
    lines = list(cart_lines(request.user))
    if not lines:
        messages.info(request, "Your cart is empty.")
        return redirect("cart:detail")

    addresses = list(request.user.addresses.all())
    subtotal = sum((line.line_total for line in lines), Decimal("0.00"))

    # The address to show as selected: the one asked for in the URL if it is
    # the customer's, otherwise their default (addresses are ordered default
    # first, so the first one is the default when there is one).
    selected = _selected_address(request, addresses)

    delivery_charge = selected.province.delivery_charge if selected else None
    total = subtotal + delivery_charge if selected else None

    # Delivery charge and days per address, so the JavaScript can update the
    # summary when the customer picks a different address (it still works
    # without JavaScript: the server uses the chosen address when placing).
    address_data = {
        address.id: {
            "charge": int(address.province.delivery_charge),
            "days": f"{address.province.est_days_min} to {address.province.est_days_max} days",
            "serviceable": address.province.is_serviceable,
        }
        for address in addresses
    }

    context = {
        "lines": lines,
        "addresses": addresses,
        "selected": selected,
        "subtotal": subtotal,
        "delivery_charge": delivery_charge,
        "total": total,
        "expected_subtotal": subtotal,
        "address_data_json": json.dumps(address_data),
    }
    return render(request, "orders/checkout.html", context)


@require_POST
@login_required
def place(request):
    """Place the order from the cart, then redirect to the confirmation page."""
    address = get_object_or_404(
        Address, pk=request.POST.get("address"), user=request.user
    )
    expected_subtotal = _parse_decimal(request.POST.get("expected_subtotal"))
    delivery_note = request.POST.get("delivery_note", "").strip()
    # Only the two methods we offer are accepted; anything else falls back to COD.
    method = request.POST.get("payment_method")
    if method != PaymentMethod.KHALTI:
        method = PaymentMethod.COD

    try:
        order = services.place_order(
            request.user, address, delivery_note, expected_subtotal,
            payment_method=method,
        )
    except services.OrderError as error:
        messages.error(request, str(error))
        return redirect("orders:checkout")

    # For Khalti, send the customer to pay; for COD, straight to confirmation.
    if order.payment_method == PaymentMethod.KHALTI:
        return redirect("payments:start", number=order.order_number)

    messages.success(request, "Your order has been placed.")
    return redirect("orders:confirmation", number=order.order_number)


@login_required
def confirmation(request, number):
    """Thank-you page shown right after an order is placed."""
    order = get_object_or_404(Order, order_number=number, user=request.user)
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def order_list(request):
    """The customer's own orders, newest first."""
    orders = request.user.orders.all()
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, number):
    """One order: its items, totals, address and the status timeline."""
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "history"),
        order_number=number,
        user=request.user,
    )
    context = {
        "order": order,
        "timeline": _build_timeline(order),
    }
    return render(request, "orders/order_detail.html", context)


@require_POST
@login_required
def cancel(request, number):
    """Cancel a Pending order (the service puts the stock back)."""
    order = get_object_or_404(Order, order_number=number, user=request.user)
    try:
        services.cancel_order(order, request.user)
        messages.success(request, "Your order has been cancelled.")
    except services.OrderError as error:
        messages.error(request, str(error))
    return redirect("orders:detail", number=order.order_number)


def _selected_address(request, addresses):
    """Pick the address to show as selected, defaulting to the first one."""
    if not addresses:
        return None
    asked = request.GET.get("address")
    for address in addresses:
        if str(address.id) == asked:
            return address
    return addresses[0]


def _parse_decimal(raw):
    """Read a money amount from the form; None if it is missing or not a number."""
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError):
        return None


def _build_timeline(order):
    """Build the list of timeline steps with each one's state and time.

    A step is 'done' once it has happened, 'current' for where the order is now,
    and 'upcoming' for later steps. A cancelled order shows the steps it reached
    as done and a final Cancelled marker.
    """
    # When each status was reached, taken from the history rows.
    reached = {row.to_status: row.changed_at for row in order.history.all()}

    if order.status == OrderStatus.CANCELLED:
        steps = []
        for status, title, note in TIMELINE_STEPS:
            if status in reached:
                steps.append({
                    "title": title, "note": note,
                    "time": reached[status], "state": "done",
                })
        steps.append({
            "title": "Cancelled",
            "note": "This order was cancelled and the stock was released.",
            "time": reached.get(OrderStatus.CANCELLED),
            "state": "current",
        })
        return steps

    current_index = [s[0] for s in TIMELINE_STEPS].index(order.status)
    steps = []
    for index, (status, title, note) in enumerate(TIMELINE_STEPS):
        if index < current_index:
            state = "done"
        elif index == current_index:
            state = "current"
        else:
            state = "upcoming"
        steps.append({
            "title": title, "note": note,
            "time": reached.get(status), "state": state,
        })
    return steps
