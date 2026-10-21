"""Order business rules.

The two things that happen to an order in this phase live here so the views
stay thin and the rules are in one place and easy to test:

- place_order: turn the cart into an order, safely, even if two people buy the
  last mattress at the same time.
- cancel_order: let a customer cancel while the order is still Pending and put
  the stock back.
"""
from decimal import Decimal

from django.db import transaction

from cart.models import CartItem
from catalog.models import ProductVariant
from core.emails import send_order_placed_email, send_order_status_email

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)


class OrderError(Exception):
    """An order action the rules do not allow (empty cart, stock gone, ...)."""


@transaction.atomic
def place_order(user, address, delivery_note, expected_subtotal,
                payment_method=PaymentMethod.COD):
    """Create an order from the user's cart and return it.

    Everything runs in one database transaction, so either the whole order is
    created and the stock reduced, or nothing changes at all. We lock the cart's
    variants while we work, re-check stock and prices on the server, and refuse
    the order if a price changed since the customer saw the summary.

    expected_subtotal is the items subtotal the customer saw; comparing it to
    the freshly added-up subtotal catches a price change. The delivery charge
    comes from the chosen address's province, so it is not part of this check.
    """
    # 1. The cart must have something in it.
    lines = list(CartItem.objects.filter(user=user).select_related("variant"))
    if not lines:
        raise OrderError("Your cart is empty.")

    # 2. We must be able to deliver to this province.
    if not address.province.is_serviceable:
        raise OrderError("We cannot deliver to that province yet.")

    # 3. Lock the cart's variants for the rest of the transaction, ordered by id.
    #    Locking stops two simultaneous checkouts from both selling the same last
    #    unit; ordering by id the same way everywhere avoids deadlocks.
    variant_ids = sorted(line.variant_id for line in lines)
    locked = ProductVariant.objects.select_for_update().filter(
        id__in=variant_ids
    ).order_by("id")
    locked_by_id = {variant.id: variant for variant in locked}

    # 4. Re-check each line against the locked, current variant, and add up the
    #    subtotal from the server's prices (never from the browser).
    subtotal = Decimal("0.00")
    for line in lines:
        variant = locked_by_id.get(line.variant_id)
        if variant is None or not variant.is_active:
            raise OrderError(
                f"{line.variant.product.name} is no longer available. "
                "Please review your cart."
            )
        if variant.stock_qty < line.quantity:
            raise OrderError(
                f"Only {variant.stock_qty} of {variant.product.name} "
                f"({variant.size.name}) left. Please update your cart."
            )
        subtotal += variant.price * line.quantity

    # 5. The subtotal must match what the customer saw on the summary page.
    #    If a price changed in between, stop and ask them to look again.
    if expected_subtotal is not None and expected_subtotal != subtotal:
        raise OrderError(
            "Prices changed while you were checking out. "
            "Please review the updated total and place the order again."
        )

    delivery_charge = address.province.delivery_charge
    total = subtotal + delivery_charge

    # 6. Create the order with a snapshot of the address and the totals.
    order = Order.objects.create(
        user=user,
        recipient=address.recipient,
        phone=address.phone,
        province_name=address.province.name,
        district=address.district,
        municipality=address.municipality,
        ward_no=address.ward_no,
        street_tole=address.street_tole,
        landmark=address.landmark,
        delivery_note=delivery_note,
        payment_method=payment_method,
        subtotal=subtotal,
        delivery_charge=delivery_charge,
        total=total,
    )
    # The id exists only after the row is saved, so build the number now.
    order.order_number = f"AR-{order.placed_at:%Y}-{order.pk:05d}"
    order.save(update_fields=["order_number"])

    # 7. Copy each cart line into an order item (a snapshot) and reduce stock.
    for line in lines:
        variant = locked_by_id[line.variant_id]
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name,
            variant_label=f"{variant.size.name} · {variant.thickness_in} in thick",
            sku=variant.sku,
            unit_price=variant.price,
            quantity=line.quantity,
            line_total=variant.price * line.quantity,
        )
        variant.stock_qty -= line.quantity
        variant.save(update_fields=["stock_qty"])

    # 8. Record the first step of the timeline.
    OrderStatusHistory.objects.create(
        order=order,
        from_status="",
        to_status=OrderStatus.PENDING,
        changed_by=user,
        note="Order placed.",
    )

    # 9. The cart is now an order, so empty it.
    CartItem.objects.filter(user=user).delete()

    # Confirmation email, sent only once this transaction commits.
    send_order_placed_email(order)

    return order


@transaction.atomic
def cancel_order(order, actor, reason=""):
    """Cancel a Pending order and put its stock back.

    Only a Pending order can be cancelled by the customer. Cancelling restores
    the stock each line took and writes a row to the order's history.
    """
    if order.status != OrderStatus.PENDING:
        raise OrderError("This order can no longer be cancelled online.")

    previous = order.status
    order.status = OrderStatus.CANCELLED
    order.save(update_fields=["status"])

    _restore_stock(order)

    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous,
        to_status=OrderStatus.CANCELLED,
        changed_by=actor,
        note=reason,
    )

    return order


# Which statuses an order may move to from each status. Delivered and Cancelled
# are the end of the line. Staff move an order forward one step; a cancel can
# happen from any step before Delivered.
ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


@transaction.atomic
def change_status(order, new_status, actor, note=""):
    """Move an order to a new status, following the allowed transitions.

    Used by staff. A cancel needs a reason and restores stock; delivering a
    Cash on Delivery order marks it Paid. Every change writes a history row.
    """
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise OrderError(
            f"An order cannot go from {order.get_status_display()} to "
            f"{OrderStatus(new_status).label}."
        )
    if new_status == OrderStatus.CANCELLED and not note.strip():
        raise OrderError("Please give a reason for cancelling the order.")

    previous = order.status
    order.status = new_status

    # Delivered cash-on-delivery orders are paid in cash at the door.
    if (
        new_status == OrderStatus.DELIVERED
        and order.payment_method == PaymentMethod.COD
    ):
        order.payment_status = PaymentStatus.PAID
    order.save(update_fields=["status", "payment_status"])

    # Cancelling frees the reserved stock.
    if new_status == OrderStatus.CANCELLED:
        _restore_stock(order)

    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous,
        to_status=new_status,
        changed_by=actor,
        note=note,
    )

    # Tell the customer, after this transaction commits.
    send_order_status_email(order)

    return order


def _restore_stock(order):
    """Add each order line's quantity back to its variant's stock."""
    for item in order.items.select_related("variant"):
        if item.variant is not None:
            item.variant.stock_qty += item.quantity
            item.variant.save(update_fields=["stock_qty"])
