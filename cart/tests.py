"""Tests for the cart: access rules, stock and per-line limits, and merging."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product, ProductVariant, Size
from core.models import StoreSettings

from .models import CartItem
from . import services

User = get_user_model()


class CartTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="buyer@example.com", password="pass12345", first_name="Bui"
        )
        cls.other = User.objects.create_user(
            email="other@example.com", password="pass12345", first_name="Oth"
        )
        cls.size = Size.objects.create(
            name="Queen", length_in=75, width_in=60, sort_order=1
        )
        cls.category = Category.objects.create(name="Memory foam", slug="memory-foam")
        cls.product = Product.objects.create(
            category=cls.category, name="AARAM Nidra", slug="aaram-nidra",
            description="Soft.", material="memory foam", firmness=2,
            warranty_months=60,
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product, size=cls.size, thickness_in=6,
            sku="AR-NID-Q6", price="29500.00", stock_qty=8,
        )
        # A scarce variant for stock-limit tests.
        cls.scarce = ProductVariant.objects.create(
            product=cls.product, size=cls.size, thickness_in=8,
            sku="AR-NID-Q8", price="33000.00", stock_qty=2,
        )

    def login(self):
        self.client.login(email="buyer@example.com", password="pass12345")


class CartAccessTests(CartTestBase):
    def test_cart_page_requires_login(self):
        response = self.client.get(reverse("cart:detail"))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={reverse('cart:detail')}"
        )

    def test_add_requires_login(self):
        response = self.client.post(
            reverse("cart:add"), {"variant": self.variant.pk, "quantity": 1}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertFalse(CartItem.objects.exists())

    def test_add_is_post_only(self):
        self.login()
        response = self.client.get(reverse("cart:add"))
        self.assertEqual(response.status_code, 405)

    def test_cannot_touch_another_users_line(self):
        self.login()
        theirs = CartItem.objects.create(
            user=self.other, variant=self.variant, quantity=1
        )
        update = self.client.post(
            reverse("cart:update", args=[theirs.pk]), {"quantity": 2}
        )
        self.assertEqual(update.status_code, 404)
        remove = self.client.post(reverse("cart:remove", args=[theirs.pk]))
        self.assertEqual(remove.status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.quantity, 1)


class CartServiceTests(CartTestBase):
    def test_add_creates_line(self):
        services.add_to_cart(self.user, self.variant, 2)
        item = CartItem.objects.get(user=self.user, variant=self.variant)
        self.assertEqual(item.quantity, 2)

    def test_adding_same_variant_merges(self):
        services.add_to_cart(self.user, self.variant, 2)
        services.add_to_cart(self.user, self.variant, 3)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 5)

    def test_cannot_exceed_stock(self):
        with self.assertRaises(services.CartError):
            services.add_to_cart(self.user, self.scarce, 3)  # only 2 in stock

    def test_merge_cannot_exceed_stock(self):
        services.add_to_cart(self.user, self.scarce, 2)
        with self.assertRaises(services.CartError):
            services.add_to_cart(self.user, self.scarce, 1)

    def test_cannot_exceed_per_line_maximum(self):
        settings = StoreSettings.load()
        settings.max_qty_per_line = 5
        settings.save()
        with self.assertRaises(services.CartError):
            services.add_to_cart(self.user, self.variant, 6)

    def test_out_of_stock_refused(self):
        self.variant.stock_qty = 0
        self.variant.save()
        with self.assertRaises(services.CartError):
            services.add_to_cart(self.user, self.variant, 1)

    def test_inactive_variant_refused(self):
        self.variant.is_active = False
        self.variant.save()
        with self.assertRaises(services.CartError):
            services.add_to_cart(self.user, self.variant, 1)

    def test_update_quantity_within_limit(self):
        item = services.add_to_cart(self.user, self.variant, 1)
        services.update_quantity(item, 4)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

    def test_update_quantity_over_stock_refused(self):
        item = services.add_to_cart(self.user, self.scarce, 1)
        with self.assertRaises(services.CartError):
            services.update_quantity(item, 3)  # only 2 in stock


class CartViewTests(CartTestBase):
    def test_add_then_cart_shows_line_and_subtotal(self):
        self.login()
        self.client.post(
            reverse("cart:add"), {"variant": self.variant.pk, "quantity": 2}
        )
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.variant.refresh_from_db()  # price is a Decimal once read back
        self.assertEqual(response.context["subtotal"], self.variant.price * 2)

    def test_cart_survives_logout_and_login(self):
        self.login()
        self.client.post(
            reverse("cart:add"), {"variant": self.variant.pk, "quantity": 1}
        )
        self.client.logout()
        self.login()
        response = self.client.get(reverse("cart:detail"))
        self.assertContains(response, self.product.name)

    def test_remove_empties_the_cart(self):
        self.login()
        item = CartItem.objects.create(
            user=self.user, variant=self.variant, quantity=1
        )
        self.client.post(reverse("cart:remove", args=[item.pk]))
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_inactive_line_dropped_when_viewing_cart(self):
        self.login()
        CartItem.objects.create(user=self.user, variant=self.variant, quantity=1)
        self.variant.is_active = False
        self.variant.save()
        response = self.client.get(reverse("cart:detail"))
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())
        self.assertEqual(response.context["subtotal"], 0)

    def test_header_cart_count(self):
        self.login()
        self.client.post(
            reverse("cart:add"), {"variant": self.variant.pk, "quantity": 2}
        )
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.context["cart_count"], 2)
