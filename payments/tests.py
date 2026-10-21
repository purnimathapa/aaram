"""Tests for Khalti payment: verify-by-lookup, the callback, and expiry.

Khalti is never actually called; its lookup and initiate are mocked, so we test
our own rules: an order is Paid only on a Completed lookup for the right amount,
a forged return URL does not mark it Paid, and unpaid orders expire.
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cart.models import CartItem
from orders import services as order_services
from orders.models import Order, OrderStatus, PaymentMethod
from orders.tests import make_world

from . import services
from .models import Payment, PaymentStatus

User = get_user_model()


def make_khalti_order(user, address, variant):
    """Place a Khalti order and a Payment attempt for its full amount."""
    CartItem.objects.create(user=user, variant=variant, quantity=1)
    order = order_services.place_order(
        user, address, "", variant.price, payment_method=PaymentMethod.KHALTI
    )
    payment = Payment.objects.create(
        order=order, pidx="px-test", amount=int(order.total * 100)
    )
    return order, payment


class VerifyPaymentTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        self.order, self.payment = make_khalti_order(
            self.user, self.address, self.variant
        )

    @patch("payments.khalti.lookup")
    def test_completed_with_right_amount_marks_paid(self, mock_lookup):
        mock_lookup.return_value = {"status": "Completed", "total_amount": self.payment.amount}
        payment, paid = services.verify_payment("px-test")
        self.assertTrue(paid)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(payment.status, PaymentStatus.COMPLETED)

    @patch("payments.khalti.lookup")
    def test_pending_does_not_mark_paid(self, mock_lookup):
        mock_lookup.return_value = {"status": "Pending", "total_amount": self.payment.amount}
        _, paid = services.verify_payment("px-test")
        self.assertFalse(paid)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "unpaid")

    @patch("payments.khalti.lookup")
    def test_wrong_amount_does_not_mark_paid(self, mock_lookup):
        mock_lookup.return_value = {"status": "Completed", "total_amount": 1}
        _, paid = services.verify_payment("px-test")
        self.assertFalse(paid)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "unpaid")


class CallbackTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        self.order, self.payment = make_khalti_order(
            self.user, self.address, self.variant
        )
        self.client.login(email="buyer@example.com", password="pass12345")

    @patch("payments.khalti.lookup")
    def test_forged_callback_params_are_ignored(self, mock_lookup):
        # The URL claims Completed, but our lookup says Pending: must stay unpaid.
        mock_lookup.return_value = {"status": "Pending", "total_amount": self.payment.amount}
        self.client.get(reverse("payments:callback"), {
            "pidx": "px-test", "status": "Completed", "amount": self.payment.amount,
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "unpaid")

    @patch("payments.khalti.lookup")
    def test_successful_callback_marks_paid(self, mock_lookup):
        mock_lookup.return_value = {"status": "Completed", "total_amount": self.payment.amount}
        response = self.client.get(reverse("payments:callback"), {"pidx": "px-test"})
        self.assertRedirects(response, self.order.get_absolute_url())
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")


class StartPaymentTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        self.client.login(email="buyer@example.com", password="pass12345")

    @patch("payments.khalti.initiate")
    def test_checkout_with_khalti_starts_a_payment(self, mock_initiate):
        mock_initiate.return_value = {"pidx": "px-9", "payment_url": "https://pay.khalti/x"}
        CartItem.objects.create(user=self.user, variant=self.variant, quantity=1)
        # Place the order choosing Khalti; it should redirect into the pay flow.
        place = self.client.post(reverse("orders:place"), {
            "address": self.address.id,
            "expected_subtotal": str(self.variant.price),
            "payment_method": "khalti",
        })
        order = Order.objects.get()
        self.assertRedirects(
            place, reverse("payments:start", args=[order.order_number]),
            fetch_redirect_response=False,
        )
        # Following start redirects out to Khalti's payment URL.
        start = self.client.get(reverse("payments:start", args=[order.order_number]))
        self.assertEqual(start.status_code, 302)
        self.assertEqual(start.url, "https://pay.khalti/x")
        self.assertTrue(Payment.objects.filter(order=order, pidx="px-9").exists())


class ExpiryCommandTests(TestCase):
    def test_expiry_cancels_old_unpaid_khalti_orders_and_restores_stock(self):
        user, address, variant = make_world(stock=5)
        order, _ = make_khalti_order(user, address, variant)
        variant.refresh_from_db()
        self.assertEqual(variant.stock_qty, 4)  # one reserved by the order

        # Make the order look 31 minutes old (bypass auto_now_add).
        old = timezone.now() - timedelta(minutes=31)
        Order.objects.filter(pk=order.pk).update(placed_at=old)

        call_command("expire_unpaid_orders")

        order.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(variant.stock_qty, 5)  # stock put back

    def test_recent_order_is_not_cancelled(self):
        user, address, variant = make_world(stock=5)
        order, _ = make_khalti_order(user, address, variant)
        call_command("expire_unpaid_orders")
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING)
