"""Tests for reviews: eligibility, one per product, and hiding."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cart.models import CartItem
from orders import services
from orders.models import OrderStatus
from orders.tests import make_world

from . import services as review_services
from .models import Review

User = get_user_model()


def deliver_an_order(user, address, variant, staff):
    """Place an order for the variant and move it all the way to Delivered."""
    CartItem.objects.create(user=user, variant=variant, quantity=1)
    order = services.place_order(user, address, "", variant.price)
    for status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING,
                   OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
        services.change_status(order, status, staff)
    return order


class EligibilityTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass12345", is_staff=True
        )
        self.product = self.variant.product

    def test_cannot_review_without_a_delivered_order(self):
        self.assertFalse(review_services.can_review(self.user, self.product))

    def test_can_review_after_delivery(self):
        deliver_an_order(self.user, self.address, self.variant, self.staff)
        self.assertTrue(review_services.can_review(self.user, self.product))

    def test_cannot_review_twice(self):
        deliver_an_order(self.user, self.address, self.variant, self.staff)
        Review.objects.create(
            user=self.user, product=self.product, rating=5, title="Good", body="Nice"
        )
        self.assertFalse(review_services.can_review(self.user, self.product))


class SubmitReviewViewTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass12345", is_staff=True
        )
        self.product = self.variant.product

    def test_ineligible_user_cannot_submit(self):
        self.client.login(email="buyer@example.com", password="pass12345")
        self.client.post(reverse("reviews:add", args=[self.product.slug]), {
            "rating": 5, "title": "Great", "body": "Loved it",
        })
        self.assertFalse(Review.objects.exists())

    def test_eligible_user_can_submit(self):
        deliver_an_order(self.user, self.address, self.variant, self.staff)
        self.client.login(email="buyer@example.com", password="pass12345")
        self.client.post(reverse("reviews:add", args=[self.product.slug]), {
            "rating": 4, "title": "Comfortable", "body": "Sleeping well",
        })
        self.assertEqual(Review.objects.filter(product=self.product).count(), 1)


class VisibilityTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        self.product = self.variant.product

    def test_hidden_review_not_shown_on_product_page(self):
        Review.objects.create(
            user=self.user, product=self.product, rating=5,
            title="Hidden one", body="secret", is_visible=False,
        )
        response = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(response, "Hidden one")
        self.assertEqual(response.context["review_count"], 0)

    def test_visible_review_counts_towards_average(self):
        Review.objects.create(
            user=self.user, product=self.product, rating=4, title="Shown", body="ok"
        )
        self.assertEqual(self.product.review_summary["count"], 1)
        self.assertEqual(self.product.review_summary["average"], 4)


class StaffHideTests(TestCase):
    def setUp(self):
        self.user, self.address, self.variant = make_world(stock=5)
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass12345", is_staff=True
        )
        self.review = Review.objects.create(
            user=self.user, product=self.variant.product, rating=5,
            title="t", body="b",
        )

    def test_staff_can_hide_and_show(self):
        self.client.login(email="staff@example.com", password="pass12345")
        self.client.post(reverse("dashboard:review_toggle", args=[self.review.pk]))
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_visible)
        self.client.post(reverse("dashboard:review_toggle", args=[self.review.pk]))
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_visible)
