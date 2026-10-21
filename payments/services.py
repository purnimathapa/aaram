"""Payment rules: start a Khalti payment and verify it by lookup.

The important rule for the defense: an order is marked Paid only when our own
server-to-server lookup says the payment is Completed for the right amount. We
never trust the status or amount that Khalti puts on the return URL, because
anyone could change those.
"""
from django.db import transaction

from orders.models import PaymentStatus as OrderPaymentStatus

from . import khalti
from .models import Payment, PaymentStatus


def start_payment(order, return_url, website_url):
    """Create a Payment attempt, ask Khalti to start it, return the payment URL."""
    amount_paisa = int(order.total * 100)  # Khalti works in paisa
    response = khalti.initiate(
        return_url=return_url,
        website_url=website_url,
        amount_paisa=amount_paisa,
        order_number=order.order_number,
        order_name=f"AARAM order {order.order_number}",
    )
    Payment.objects.create(
        order=order,
        pidx=response.get("pidx", ""),
        amount=amount_paisa,
        status=PaymentStatus.INITIATED,
    )
    return response["payment_url"]


@transaction.atomic
def verify_payment(pidx):
    """Look the payment up at Khalti and mark the order Paid only if Completed.

    Returns (payment, paid). paid is True only when Khalti reports Completed for
    the exact amount we charged.
    """
    payment = Payment.objects.select_related("order").filter(pidx=pidx).first()
    if payment is None:
        return None, False

    data = khalti.lookup(pidx)
    payment.raw_response = data
    status = data.get("status")
    total_amount = data.get("total_amount")

    if status == "Completed" and total_amount == payment.amount:
        payment.status = PaymentStatus.COMPLETED
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        order = payment.order
        order.payment_status = OrderPaymentStatus.PAID
        order.save(update_fields=["payment_status"])
        return payment, True

    # Anything else (Pending, Expired, User canceled, wrong amount) is not paid.
    if status in {"Expired", "User canceled", "Failed"}:
        payment.status = PaymentStatus.FAILED
    payment.save(update_fields=["status", "raw_response", "updated_at"])
    return payment, False
