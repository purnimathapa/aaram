"""Khalti payment views: start a payment and handle the return (callback)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from orders.models import Order, OrderStatus, PaymentStatus

from . import khalti, services


@login_required
def start(request, number):
    """Start (or retry) a Khalti payment for the customer's own order."""
    order = get_object_or_404(Order, order_number=number, user=request.user)

    # Only an unpaid, still-pending Khalti order can be paid online.
    if order.payment_status == PaymentStatus.PAID or order.status != OrderStatus.PENDING:
        messages.info(request, "This order cannot be paid online now.")
        return redirect(order.get_absolute_url())

    return_url = request.build_absolute_uri(reverse("payments:callback"))
    website_url = request.build_absolute_uri("/")
    try:
        payment_url = services.start_payment(order, return_url, website_url)
    except khalti.KhaltiError:
        messages.error(request, "Could not reach Khalti. Please try again.")
        return redirect(order.get_absolute_url())
    return redirect(payment_url)


@login_required
def callback(request):
    """Where Khalti returns the customer. We verify by lookup, not by the URL."""
    pidx = request.GET.get("pidx")
    if not pidx:
        messages.error(request, "Payment could not be identified.")
        return redirect("orders:list")

    try:
        payment, paid = services.verify_payment(pidx)
    except khalti.KhaltiError:
        messages.error(request, "Could not confirm the payment with Khalti.")
        return redirect("orders:list")

    # The payment must exist and belong to the logged-in customer.
    if payment is None or payment.order.user != request.user:
        messages.error(request, "Payment could not be matched to your order.")
        return redirect("orders:list")

    if paid:
        messages.success(request, "Payment received. Thank you.")
    else:
        messages.error(
            request, "Payment was not completed. You can try paying again."
        )
    return redirect(payment.order.get_absolute_url())
