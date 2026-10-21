"""Public catalogue: the listing with search, filters and sort, and the
product detail page with its variant picker.

Only active products and active variants are shown. The listing keeps all of
its state (search, filters, sort, page) in the URL query string, so a filtered
view can be bookmarked and shared and works without JavaScript.
"""
import json

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Min, Prefetch, Q
from django.shortcuts import get_object_or_404, render

from core.models import Province, StoreSettings
from reviews.forms import ReviewForm
from reviews.services import can_review

from .models import Category, Product, ProductVariant, Size

PAGE_SIZE = 12

# At or below this many in stock, show "Only N left" instead of "In stock".
LOW_STOCK = 3

# Firmness filter buckets, matching the mockup's three groups.
FIRMNESS_BUCKETS = {
    "soft": [1, 2],
    "medium": [3],
    "firm": [4, 5],
}

# Query-string value -> order_by field. min_price is annotated below.
SORT_OPTIONS = {
    "popular": "name",
    "price-asc": "min_price",
    "price-desc": "-min_price",
    "newest": "-id",
}


def _parse_int(value):
    """Return value as an int, or None if it is missing or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def catalogue(request):
    """List active products with search, filters, sort and pagination."""
    active_variants = ProductVariant.objects.filter(is_active=True)
    products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related(
            Prefetch("variants", queryset=active_variants.select_related("size")),
            "reviews",  # for the average rating shown on each card
        )
        # Lowest active price per product, used for display and price sorting.
        .annotate(min_price=Min("variants__price", filter=Q(variants__is_active=True)))
    )

    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(material__icontains=query)
            | Q(category__name__icontains=query)
        )

    selected_categories = request.GET.getlist("category")
    if selected_categories:
        products = products.filter(category__slug__in=selected_categories)

    selected_sizes = request.GET.getlist("size")
    if selected_sizes:
        products = products.filter(
            variants__size__name__in=selected_sizes, variants__is_active=True
        )

    selected_firmness = request.GET.getlist("firmness")
    levels = []
    for bucket in selected_firmness:
        levels.extend(FIRMNESS_BUCKETS.get(bucket, []))
    if levels:
        products = products.filter(firmness__in=levels)

    price_min = _parse_int(request.GET.get("price_min"))
    if price_min is not None:
        products = products.filter(min_price__gte=price_min)
    price_max = _parse_int(request.GET.get("price_max"))
    if price_max is not None:
        products = products.filter(min_price__lte=price_max)

    if request.GET.get("in_stock"):
        products = products.filter(variants__stock_qty__gt=0, variants__is_active=True)

    # Joins through variants can duplicate rows, so collapse them.
    products = products.distinct()

    sort = request.GET.get("sort", "popular")
    products = products.order_by(SORT_OPTIONS.get(sort, "name"))

    paginator = Paginator(products, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    # Current filters without the page number, for the pagination links.
    params = request.GET.copy()
    params.pop("page", None)
    base_query = params.urlencode()

    context = {
        "page": page,
        "base_query": base_query,
        "total": paginator.count,
        "query": query,
        "categories": Category.objects.filter(is_active=True),
        "sizes": Size.objects.all(),
        "selected_categories": selected_categories,
        "selected_sizes": selected_sizes,
        "selected_firmness": selected_firmness,
        "price_min": request.GET.get("price_min", ""),
        "price_max": request.GET.get("price_max", ""),
        "in_stock": bool(request.GET.get("in_stock")),
        "sort": sort,
    }
    return render(request, "catalog/catalogue.html", context)


def _variant_status(stock_qty):
    """Return a (text, css modifier) pair describing a variant's stock."""
    if stock_qty <= 0:
        return "Out of stock", "bad"
    if stock_qty <= LOW_STOCK:
        return f"Only {stock_qty} left", "warn"
    return "In stock", "ok"


def product_detail(request, slug):
    """Show one active product, its variants, and the variant picker data.

    The picker updates price and stock with JavaScript from the data below. The
    no-JS path reads ?size= and ?thickness= and renders the chosen variant on
    the server, so the page works without JavaScript.
    """
    product = get_object_or_404(
        Product.objects.select_related("category"), slug=slug, is_active=True
    )
    variants = list(product.variants.filter(is_active=True).select_related("size"))

    # Options to show as chips, in display order and without duplicates.
    sizes, seen_sizes = [], set()
    thicknesses = set()
    for variant in variants:
        if variant.size_id not in seen_sizes:
            seen_sizes.add(variant.size_id)
            sizes.append(variant.size)
        thicknesses.add(variant.thickness_in)
    thicknesses = sorted(thicknesses)

    # Data the JavaScript picker reads, keyed by "<size id>-<thickness>".
    variant_data = {}
    for variant in variants:
        text, modifier = _variant_status(variant.stock_qty)
        variant_data[f"{variant.size_id}-{variant.thickness_in}"] = {
            "id": variant.id,
            "price": int(variant.price),
            "sku": variant.sku,
            "stock": variant.stock_qty,
            "status_text": text,
            "status_modifier": modifier,
            "variant_line": (
                f"{variant.size.name} · {variant.size.length_in} × "
                f"{variant.size.width_in} in · {variant.thickness_in} in thick · "
                f"SKU {variant.sku}"
            ),
        }

    # Pick the variant to show first: the URL choice, else the first in stock.
    chosen_size = _parse_int(request.GET.get("size"))
    chosen_thickness = _parse_int(request.GET.get("thickness"))
    selected = None
    if chosen_size is not None and chosen_thickness is not None:
        selected = next(
            (
                v
                for v in variants
                if v.size_id == chosen_size and v.thickness_in == chosen_thickness
            ),
            None,
        )
    if selected is None:
        selected = next((v for v in variants if v.stock_qty > 0), None)
    if selected is None and variants:
        selected = variants[0]

    selected_status = _variant_status(selected.stock_qty) if selected else ("", "")

    max_qty_per_line = StoreSettings.load().max_qty_per_line

    provinces = list(Province.objects.all())
    province_data = {
        p.name: {
            "charge": int(p.delivery_charge),
            "days": f"{p.est_days_min} to {p.est_days_max} days",
        }
        for p in provinces
    }
    # Default the delivery box to the first serviceable province.
    default_province = next((p for p in provinces if p.is_serviceable), None)

    # Visible reviews, their average and count, and whether this user may review.
    reviews = list(product.reviews.filter(is_visible=True).select_related("user"))
    rating = product.reviews.filter(is_visible=True).aggregate(
        average=Avg("rating"), count=Count("id")
    )

    context = {
        "product": product,
        "sizes": sizes,
        "thicknesses": thicknesses,
        "selected": selected,
        "selected_status_text": selected_status[0],
        "selected_status_modifier": selected_status[1],
        "max_qty_per_line": max_qty_per_line,
        "firmness_scale": [1, 2, 3, 4, 5],
        "variant_data_json": json.dumps(variant_data),
        "provinces": provinces,
        "province_data_json": json.dumps(province_data),
        "default_province": default_province,
        "reviews": reviews,
        "avg_rating": rating["average"],
        "review_count": rating["count"],
        "can_review": can_review(request.user, product),
        "review_form": ReviewForm(),
    }
    return render(request, "catalog/product_detail.html", context)
