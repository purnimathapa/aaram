"""Tests for checkout and orders.

These cover the rules that matter for the defense: the server recalculates
money, stock is reduced safely (including two buyers racing for the last unit),
snapshots are stored, a customer only sees their own orders, and cancelling a
Pending order puts the stock back.
"""
import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from accounts.models import Address
from cart.models import CartItem
from catalog.models import Category, Product, ProductVariant, Size
from core.models import Province

from . import services
from .models import Order, OrderItem, OrderStatus

User = get_user_model()


def make_world(stock=5, serviceable=True):
    """Create a user, an address and one product variant with the given stock."""
    user = User.objects.create_user(
        email="buyer@example.com", password="pass12345", first_name="Bui"
    )
    province = Province.objects.create(
        name="Bagmati", delivery_charge=Decimal("500.00"),
        est_days_min=2, est_days_max=4, is_serviceable=serviceable,
    )
    address = Address.objects.create(
        user=user, province=province, recipient="Bui Buyer", phone="9812345678",
        district="Kathmandu", municipality="KMC", ward_no=10,
        street_tole="Baneshwor", is_default=True,
    )
    category = Category.objects.create(name="Memory foam", slug="memory-foam")
    product = Product.objects.create(
        category=category, name="AARAM Nidra", slug="aaram-nidra",
        description="Soft.", material="memory foam", firmness=2,
        warranty_months=60,
    )
    size = Size.objects.create(name="Queen", length_in=75, width_in=60, sort_order=1)
    variant = ProductVariant.objects.create(
        product=product, size=size, thickness_in=8,
        sku="AR-NID-Q8", price=Decimal("29500.00"), stock_qty=stock,
    )
    return user, address, variant


class CheckoutServiceTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        CartItem.objects.create(user=self.user, variant=self.variant, quantity=2)

    def test_place_order_builds_order_with_snapshots(self):
        order = services.place_order(
            self.user, self.address, "", expected_subtotal=Decimal("59000.00")
        )
        # Totals are computed on the server.
        self.assertEqual(order.subtotal, Decimal("59000.00"))
        self.assertEqual(order.delivery_charge, Decimal("500.00"))
        self.assertEqual(order.total, Decimal("59500.00"))
        # The order item keeps a snapshot of the variant.
        item = order.items.get()
        self.assertEqual(item.product_name, "AARAM Nidra")
        self.assertEqual(item.sku, "AR-NID-Q8")
        self.assertEqual(item.unit_price, Decimal("29500.00"))
        self.assertEqual(item.line_total, Decimal("59000.00"))
        # The address is snapshotted onto the order.
        self.assertEqual(order.recipient, "Bui Buyer")
        self.assertEqual(order.province_name, "Bagmati")

    def test_place_order_reduces_stock_and_clears_cart(self):
        services.place_order(self.user, self.address, "", Decimal("59000.00"))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 3)  # 5 - 2
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_order_number_format(self):
        order = services.place_order(self.user, self.address, "", Decimal("59000.00"))
        self.assertRegex(order.order_number, r"^AR-\d{4}-\d{5}$")

    def test_first_history_row_written(self):
        order = services.place_order(self.user, self.address, "", Decimal("59000.00"))
        row = order.history.get()
        self.assertEqual(row.to_status, OrderStatus.PENDING)

    def test_price_change_is_caught(self):
        # Customer saw a lower subtotal than the current prices add up to.
        with self.assertRaises(services.OrderError):
            services.place_order(
                self.user, self.address, "", expected_subtotal=Decimal("40000.00")
            )
        self.assertFalse(Order.objects.exists())

    def test_insufficient_stock_blocks_order(self):
        self.variant.stock_qty = 1  # cart wants 2
        self.variant.save()
        with self.assertRaises(services.OrderError):
            services.place_order(self.user, self.address, "", Decimal("59000.00"))
        self.assertFalse(Order.objects.exists())

    def test_empty_cart_blocks_order(self):
        CartItem.objects.filter(user=self.user).delete()
        with self.assertRaises(services.OrderError):
            services.place_order(self.user, self.address, "", None)

    def test_unserviceable_province_blocks_order(self):
        self.address.province.is_serviceable = False
        self.address.province.save()
        with self.assertRaises(services.OrderError):
            services.place_order(self.user, self.address, "", Decimal("59000.00"))


class CancelTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        CartItem.objects.create(user=self.user, variant=self.variant, quantity=2)
        self.order = services.place_order(
            self.user, self.address, "", Decimal("59000.00")
        )

    def test_cancel_pending_restores_stock(self):
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 3)
        services.cancel_order(self.order, self.user, reason="Changed my mind")
        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)
        self.assertEqual(self.variant.stock_qty, 5)  # stock put back

    def test_cannot_cancel_non_pending(self):
        self.order.status = OrderStatus.SHIPPED
        self.order.save()
        with self.assertRaises(services.OrderError):
            services.cancel_order(self.order, self.user)


class CheckoutViewTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        CartItem.objects.create(user=self.user, variant=self.variant, quantity=1)

    def login(self):
        self.client.login(email="buyer@example.com", password="pass12345")

    def test_checkout_requires_login(self):
        response = self.client.get(reverse("orders:checkout"))
        self.assertIn(reverse("accounts:login"), response.url)

    def test_checkout_shows_summary(self):
        self.login()
        response = self.client.get(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["subtotal"], Decimal("29500.00"))
        self.assertEqual(response.context["total"], Decimal("30000.00"))

    def test_place_order_end_to_end(self):
        self.login()
        response = self.client.post(reverse("orders:place"), {
            "address": self.address.id,
            "expected_subtotal": "29500.00",
            "delivery_note": "Call first",
        })
        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse("orders:confirmation", args=[order.order_number]),
        )
        self.assertEqual(order.delivery_note, "Call first")

    def test_order_pages_render_for_owner(self):
        self.login()
        order = services.place_order(self.user, self.address, "", Decimal("29500.00"))
        for url in [
            reverse("orders:list"),
            order.get_absolute_url(),
            reverse("orders:confirmation", args=[order.order_number]),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, order.order_number)

    def test_customer_can_cancel_pending_order_via_view(self):
        self.login()
        order = services.place_order(self.user, self.address, "", Decimal("29500.00"))
        response = self.client.post(reverse("orders:cancel", args=[order.order_number]))
        self.assertRedirects(response, order.get_absolute_url())
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_cannot_view_another_users_order(self):
        other = User.objects.create_user(email="other@example.com", password="pass12345")
        order = services.place_order(self.user, self.address, "", Decimal("29500.00"))
        self.client.login(email="other@example.com", password="pass12345")
        response = self.client.get(order.get_absolute_url())
        self.assertEqual(response.status_code, 404)


class CheckoutConcurrencyTest(TransactionTestCase):
    """Two customers try to buy the last unit at the same time."""

    def test_only_one_of_two_racing_checkouts_succeeds(self):
        # One unit in stock; two customers each want it.
        buyer_one, address_one, variant = make_world(stock=1)
        buyer_two = User.objects.create_user(
            email="two@example.com", password="pass12345", first_name="Two"
        )
        address_two = Address.objects.create(
            user=buyer_two, province=address_one.province, recipient="Two",
            phone="9812345679", district="Kathmandu", municipality="KMC",
            ward_no=5, street_tole="Lagan", is_default=True,
        )
        CartItem.objects.create(user=buyer_one, variant=variant, quantity=1)
        CartItem.objects.create(user=buyer_two, variant=variant, quantity=1)

        results = {}
        barrier = threading.Barrier(2)

        def attempt(user, address, key):
            barrier.wait()  # start both at the same moment
            try:
                services.place_order(user, address, "", Decimal("29500.00"))
                results[key] = "ok"
            except services.OrderError:
                results[key] = "failed"
            finally:
                # Each thread uses its own DB connection; close it when done.
                connections.close_all()

        threads = [
            threading.Thread(target=attempt, args=(buyer_one, address_one, "one")),
            threading.Thread(target=attempt, args=(buyer_two, address_two, "two")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Exactly one order exists, and the stock is now zero.
        self.assertEqual(Order.objects.count(), 1)
        variant.refresh_from_db()
        self.assertEqual(variant.stock_qty, 0)
        self.assertEqual(sorted(results.values()), ["failed", "ok"])
