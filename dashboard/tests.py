"""Tests for the staff dashboard: access control and the main actions."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cart.models import CartItem
from catalog.models import Category, Product, ProductVariant, Size
from orders import services
from orders.models import Order, OrderStatus
from orders.tests import make_world

User = get_user_model()


class StaffAccessTests(TestCase):
    """Every /staff/ page must refuse visitors and ordinary customers."""

    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust@example.com", password="pass12345"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass12345", is_staff=True
        )
        self.urls = [
            reverse("dashboard:home"),
            reverse("dashboard:order_list"),
            reverse("dashboard:product_list"),
            reverse("dashboard:product_new"),
            reverse("dashboard:inventory"),
            reverse("dashboard:customer_list"),
        ]

    def test_visitor_is_sent_to_login(self):
        for url in self.urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_customer_is_forbidden(self):
        self.client.login(email="cust@example.com", password="pass12345")
        for url in self.urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_staff_can_open_the_pages(self):
        self.client.login(email="staff@example.com", password="pass12345")
        for url in self.urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)


class StaffActionTests(TestCase):
    def setUp(self):
        self.customer, self.address, self.variant = make_world(stock=5)
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass12345", is_staff=True
        )
        CartItem.objects.create(user=self.customer, variant=self.variant, quantity=2)
        self.order = services.place_order(
            self.customer, self.address, "", Decimal("59000.00")
        )
        self.client.login(email="staff@example.com", password="pass12345")

    def test_order_status_action_moves_order_forward(self):
        response = self.client.post(
            reverse("dashboard:order_status", args=[self.order.order_number]),
            {"new_status": OrderStatus.CONFIRMED},
        )
        self.assertRedirects(
            response, reverse("dashboard:order_detail", args=[self.order.order_number])
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CONFIRMED)

    def test_order_detail_page_renders(self):
        response = self.client.get(
            reverse("dashboard:order_detail", args=[self.order.order_number])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_inventory_adjust_rejects_negative(self):
        response = self.client.post(
            reverse("dashboard:inventory_adjust", args=[self.variant.pk]),
            {"stock_qty": "-5"},
        )
        self.assertRedirects(response, reverse("dashboard:inventory"))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 3)  # unchanged (5 - 2 from order)

    def test_inventory_adjust_sets_new_stock(self):
        self.client.post(
            reverse("dashboard:inventory_adjust", args=[self.variant.pk]),
            {"stock_qty": "20"},
        )
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 20)

    def test_dashboard_pending_kpi_matches_data(self):
        response = self.client.get(reverse("dashboard:home"))
        pending_kpi = next(k for k in response.context["kpis"] if k["label"] == "Pending orders")
        self.assertEqual(pending_kpi["value"], 1)

    def test_customer_list_excludes_staff_and_counts_orders(self):
        response = self.client.get(reverse("dashboard:customer_list"))
        customers = list(response.context["customers"])
        self.assertIn(self.customer, customers)
        self.assertNotIn(self.staff, customers)
        self.assertEqual(customers[0].order_count, 1)


class ProductEditorTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass12345", is_staff=True
        )
        self.category = Category.objects.create(name="Memory foam", slug="memory-foam")
        self.size = Size.objects.create(name="Queen", length_in=75, width_in=60, sort_order=1)
        self.client.login(email="staff@example.com", password="pass12345")

    def test_create_product_with_a_variant(self):
        response = self.client.post(reverse("dashboard:product_new"), {
            "category": self.category.id,
            "name": "AARAM Sutra",
            "slug": "aaram-sutra",
            "description": "A new mattress.",
            "material": "memory foam",
            "firmness": 3,
            "warranty_months": 60,
            "is_active": "on",
            # Variant formset: one row.
            "variants-TOTAL_FORMS": "1",
            "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "0",
            "variants-MAX_NUM_FORMS": "1000",
            "variants-0-size": self.size.id,
            "variants-0-thickness_in": "6",
            "variants-0-sku": "AR-SUT-Q6",
            "variants-0-price": "25000.00",
            "variants-0-stock_qty": "10",
            "variants-0-is_active": "on",
            # Image formset: no rows.
            "images-TOTAL_FORMS": "0",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
        })
        self.assertRedirects(response, reverse("dashboard:product_list"))
        product = Product.objects.get(slug="aaram-sutra")
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.variants.get().sku, "AR-SUT-Q6")

    def test_edit_page_renders(self):
        product = Product.objects.create(
            category=self.category, name="AARAM Nidra", slug="aaram-nidra",
            description="x", material="memory foam", firmness=2, warranty_months=60,
        )
        response = self.client.get(reverse("dashboard:product_edit", args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AARAM Nidra")
