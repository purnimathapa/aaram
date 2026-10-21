"""Tests for store emails and the on-commit sending behaviour."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction
from django.test import TestCase
from django.urls import reverse

from cart.models import CartItem
from orders import services
from orders.tests import make_world

User = get_user_model()


class EmailTests(TestCase):
    def test_registration_sends_a_welcome_email(self):
        # captureOnCommitCallbacks runs the on_commit email send inside the test.
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("accounts:register"), {
                "first_name": "Bina", "last_name": "Thapa",
                "email": "bina@example.com", "phone": "9812345678",
                "password1": "strongpass123", "password2": "strongpass123",
            })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome", mail.outbox[0].subject)

    def test_placing_an_order_sends_a_confirmation(self):
        user, address, variant = make_world(stock=5)
        CartItem.objects.create(user=user, variant=variant, quantity=1)
        with self.captureOnCommitCallbacks(execute=True):
            services.place_order(user, address, "", variant.price)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("received your order", mail.outbox[0].subject)

    def test_no_email_if_the_order_transaction_rolls_back(self):
        user, address, variant = make_world(stock=5)
        CartItem.objects.create(user=user, variant=variant, quantity=1)
        # Force a rollback around place_order; the on_commit email must not fire.
        try:
            with transaction.atomic():
                services.place_order(user, address, "", variant.price)
                raise RuntimeError("rollback")
        except RuntimeError:
            pass
        self.assertEqual(len(mail.outbox), 0)
