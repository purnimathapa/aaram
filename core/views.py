"""Public store pages."""
from django.db.models import Avg, Min, Prefetch

from django.shortcuts import render

from catalog.models import Category, Product, ProductVariant, Size


def home(request):
    """Render the home page with the shop-by-feel, popular and size sections."""
    active_variants = ProductVariant.objects.filter(is_active=True)

    categories = []
    for category in Category.objects.filter(is_active=True):
        average = category.products.filter(is_active=True).aggregate(
            avg=Avg("firmness")
        )["avg"]
        # Round the category's typical firmness to a 1-5 dot count for display.
        categories.append(
            {"category": category, "firmness": round(average) if average else 0}
        )

    popular = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related(Prefetch("variants", queryset=active_variants), "reviews")
        .annotate(min_price=Min("variants__price"))[:4]
    )

    context = {
        "feel_categories": categories,
        "popular": popular,
        "sizes": Size.objects.all(),
    }
    return render(request, "core/home.html", context)
