"""Tests for the catalogue: search, filters, sort, and hiding inactive items."""
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import IntegrityError, connection, transaction
from django.urls import reverse

from .models import Category, Product, ProductVariant, Size


class CatalogueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.single = Size.objects.create(name="Single", length_in=72, width_in=36, sort_order=1)
        cls.queen = Size.objects.create(name="Queen", length_in=75, width_in=60, sort_order=3)

        cls.memory = Category.objects.create(name="Memory foam", slug="memory-foam")
        cls.ortho = Category.objects.create(name="Orthopedic", slug="orthopedic")

        cls.nidra = Product.objects.create(
            category=cls.memory, name="AARAM Nidra", slug="aaram-nidra",
            description="Soft memory foam.", material="memory foam and PU core",
            firmness=2, warranty_months=60,
        )
        ProductVariant.objects.create(
            product=cls.nidra, size=cls.single, thickness_in=6,
            sku="AR-NID-S6", price="18500.00", stock_qty=0,
        )
        ProductVariant.objects.create(
            product=cls.nidra, size=cls.queen, thickness_in=6,
            sku="AR-NID-Q6", price="29500.00", stock_qty=5,
        )

        cls.himal = Product.objects.create(
            category=cls.ortho, name="AARAM Himal Ortho", slug="aaram-himal-ortho",
            description="Firm support.", material="high-density foam core",
            firmness=5, warranty_months=84,
        )
        ProductVariant.objects.create(
            product=cls.himal, size=cls.queen, thickness_in=6,
            sku="AR-HIM-Q6", price="33000.00", stock_qty=10,
        )

        # All-zero-stock product, to test the in-stock filter.
        cls.empty = Product.objects.create(
            category=cls.memory, name="AARAM Khali", slug="aaram-khali",
            description="Out of stock.", material="memory foam",
            firmness=3, warranty_months=60,
        )
        ProductVariant.objects.create(
            product=cls.empty, size=cls.queen, thickness_in=6,
            sku="AR-KHA-Q6", price="21000.00", stock_qty=0,
        )

        # Inactive product, which must never appear.
        cls.hidden = Product.objects.create(
            category=cls.memory, name="AARAM Gupt", slug="aaram-gupt",
            description="Hidden.", material="memory foam",
            firmness=3, warranty_months=60, is_active=False,
        )
        ProductVariant.objects.create(
            product=cls.hidden, size=cls.queen, thickness_in=6,
            sku="AR-GUP-Q6", price="20000.00", stock_qty=5,
        )

    def _names(self, response):
        return {p.name for p in response.context["page"].object_list}

    def test_search_by_name(self):
        response = self.client.get(reverse("catalog:catalogue"), {"q": "Nidra"})
        self.assertEqual(self._names(response), {"AARAM Nidra"})

    def test_search_by_material(self):
        response = self.client.get(reverse("catalog:catalogue"), {"q": "high-density"})
        self.assertEqual(self._names(response), {"AARAM Himal Ortho"})

    def test_search_by_category(self):
        response = self.client.get(reverse("catalog:catalogue"), {"q": "Orthopedic"})
        self.assertEqual(self._names(response), {"AARAM Himal Ortho"})

    def test_filter_by_category(self):
        response = self.client.get(reverse("catalog:catalogue"), {"category": "orthopedic"})
        self.assertEqual(self._names(response), {"AARAM Himal Ortho"})

    def test_filter_by_size(self):
        response = self.client.get(reverse("catalog:catalogue"), {"size": "Single"})
        self.assertEqual(self._names(response), {"AARAM Nidra"})

    def test_filter_by_firmness_firm_bucket(self):
        response = self.client.get(reverse("catalog:catalogue"), {"firmness": "firm"})
        self.assertEqual(self._names(response), {"AARAM Himal Ortho"})

    def test_price_range_minimum(self):
        response = self.client.get(reverse("catalog:catalogue"), {"price_min": "30000"})
        self.assertEqual(self._names(response), {"AARAM Himal Ortho"})

    def test_in_stock_only_hides_sold_out_products(self):
        response = self.client.get(reverse("catalog:catalogue"), {"in_stock": "1"})
        names = self._names(response)
        self.assertIn("AARAM Nidra", names)
        self.assertIn("AARAM Himal Ortho", names)
        self.assertNotIn("AARAM Khali", names)

    def test_inactive_product_hidden_from_listing(self):
        response = self.client.get(reverse("catalog:catalogue"))
        self.assertNotIn("AARAM Gupt", self._names(response))

    def test_inactive_product_detail_returns_404(self):
        response = self.client.get(
            reverse("catalog:product_detail", args=["aaram-gupt"])
        )
        self.assertEqual(response.status_code, 404)

    def test_active_product_detail_shows_price(self):
        response = self.client.get(
            reverse("catalog:product_detail", args=["aaram-nidra"])
        )
        self.assertEqual(response.status_code, 200)
        # The in-stock Queen variant is chosen first (Single is sold out).
        self.assertEqual(response.context["selected"].sku, "AR-NID-Q6")

    def test_sort_price_low_to_high(self):
        response = self.client.get(reverse("catalog:catalogue"), {"sort": "price-asc"})
        prices = [p.min_price for p in response.context["page"].object_list]
        self.assertEqual(prices, sorted(prices))

    def test_catalogue_uses_few_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("catalog:catalogue"))
        # Listing many products must not run a query per product (no N+1).
        self.assertLessEqual(len(ctx.captured_queries), 8)


class VariantConstraintTests(TestCase):
    """The database itself must reject bad variant data."""

    @classmethod
    def setUpTestData(cls):
        cls.size = Size.objects.create(name="Queen", length_in=75, width_in=60, sort_order=1)
        cls.category = Category.objects.create(name="Memory foam", slug="memory-foam")
        cls.product = Product.objects.create(
            category=cls.category, name="AARAM Nidra", slug="aaram-nidra",
            description="Soft.", material="memory foam", firmness=2, warranty_months=60,
        )
        ProductVariant.objects.create(
            product=cls.product, size=cls.size, thickness_in=6,
            sku="AR-NID-Q6", price="29500.00", stock_qty=5,
        )

    def test_price_must_be_positive(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductVariant.objects.create(
                product=self.product, size=self.size, thickness_in=8,
                sku="AR-NID-Q8", price="0.00", stock_qty=5,
            )

    def test_stock_cannot_be_negative(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductVariant.objects.create(
                product=self.product, size=self.size, thickness_in=10,
                sku="AR-NID-Q10", price="30000.00", stock_qty=-1,
            )

    def test_sku_must_be_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductVariant.objects.create(
                product=self.product, size=self.size, thickness_in=8,
                sku="AR-NID-Q6", price="30000.00", stock_qty=5,  # duplicate SKU
            )
