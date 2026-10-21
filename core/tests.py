"""Tests for the core store pages and template filters."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.templatetags.core_extras import npr


class HomePageTests(TestCase):
    def test_home_returns_200_and_uses_base_template(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")


class NprFilterTests(TestCase):
    def test_nepali_grouping(self):
        self.assertEqual(npr(500), "Rs. 500")
        self.assertEqual(npr(1500), "Rs. 1,500")
        self.assertEqual(npr(29500), "Rs. 29,500")
        self.assertEqual(npr(125000), "Rs. 1,25,000")
        self.assertEqual(npr(1250000), "Rs. 12,50,000")

    def test_accepts_decimal_and_rounds_to_rupees(self):
        self.assertEqual(npr(Decimal("29500.00")), "Rs. 29,500")
        self.assertEqual(npr(Decimal("29500.49")), "Rs. 29,500")

    def test_invalid_value_returns_empty_string(self):
        self.assertEqual(npr("not a number"), "")
        self.assertEqual(npr(None), "")
