"""Staff dashboard views, all protected by @staff_required.

Sections below: the dashboard home (KPIs and simple charts), order management
(list, detail, status actions), product management (list and the editor with
its formsets), inventory (stock per variant with a quick adjust) and a
read-only customer list.

Numbers for the dashboard come from database queries (aggregation), never from
anything the browser sends.
"""
from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from catalog.models import Product, ProductVariant
from core.models import StoreSettings
from orders import services
from orders.models import Order, OrderStatus, PaymentStatus
from reviews.models import Review

from .forms import ImageFormSet, ProductForm, VariantFormSet
from .permissions import staff_required


# The next step a staff member can move an order to, and the button wording.
NEXT_ACTION = {
    OrderStatus.PENDING: (OrderStatus.CONFIRMED, "Confirm order"),
    OrderStatus.CONFIRMED: (OrderStatus.PROCESSING, "Start processing"),
    OrderStatus.PROCESSING: (OrderStatus.SHIPPED, "Mark as shipped"),
    OrderStatus.SHIPPED: (OrderStatus.DELIVERED, "Mark as delivered"),
}


# ---------- Dashboard home ----------

def _period_start(period):
    """Return the first date to count from for the chosen period."""
    today = timezone.localdate()
    if period == "today":
        return today
    if period == "7days":
        return today - timedelta(days=6)
    # Default: this month.
    return today.replace(day=1)


@staff_required
def dashboard_home(request):
    """KPI tiles, recent orders, the low-stock list and two simple charts."""
    settings = StoreSettings.load()
    period = request.GET.get("period", "month")
    start = _period_start(period)

    # Orders placed in the period, and the sales from delivered ones.
    in_period = Order.objects.filter(placed_at__date__gte=start)
    sales = (
        in_period.filter(status=OrderStatus.DELIVERED)
        .aggregate(total=Sum("total"))["total"]
        or 0
    )
    low_stock = (
        ProductVariant.objects.filter(
            is_active=True, stock_qty__lte=settings.low_stock_threshold
        )
        .select_related("product", "size")
        .order_by("stock_qty")
    )

    kpis = [
        {"label": "Pending orders", "value": Order.objects.filter(status=OrderStatus.PENDING).count(), "sub": "waiting for a confirmation call"},
        {"label": "Orders this period", "value": in_period.count(), "sub": _period_label(period)},
        {"label": "Sales this period", "value": sales, "sub": "from delivered orders", "money": True},
        {"label": "Low-stock sizes", "value": low_stock.count(), "sub": f"{settings.low_stock_threshold} or fewer left"},
    ]

    context = {
        "period": period,
        "kpis": kpis,
        "recent_orders": Order.objects.select_related("user")[:8],
        "low_stock": low_stock,
        "active": "home",
        "orders_per_day": _orders_per_day(in_period),
        "sales_by_province": _sales_by_province(in_period),
    }
    return render(request, "dashboard/home.html", context)


def _period_label(period):
    return {"today": "today", "7days": "in the last 7 days"}.get(period, "this month")


def _orders_per_day(orders):
    """Count orders per day and give each a bar height percentage."""
    rows = (
        orders.values("placed_at__date")
        .annotate(n=Count("id"))
        .order_by("placed_at__date")
    )
    counts = [{"label": r["placed_at__date"].strftime("%d %b"), "n": r["n"]} for r in rows]
    busiest = max((r["n"] for r in counts), default=0)
    for row in counts:
        row["height"] = round(row["n"] / busiest * 100) if busiest else 0
    return counts


def _sales_by_province(orders):
    """Sum delivered-order sales per province, with a bar width percentage."""
    rows = (
        orders.filter(status=OrderStatus.DELIVERED)
        .values("province_name")
        .annotate(amount=Sum("total"))
        .order_by("-amount")
    )
    top = rows[0]["amount"] if rows else 0
    result = []
    for row in rows:
        result.append({
            "name": row["province_name"],
            "amount": row["amount"],
            "width": round(row["amount"] / top * 100) if top else 0,
        })
    return result


# ---------- Orders ----------

@staff_required
def order_list(request):
    """All orders, with filters for status and province and a number search."""
    orders = Order.objects.select_related("user")

    status = request.GET.get("status", "")
    if status:
        orders = orders.filter(status=status)
    province = request.GET.get("province", "")
    if province:
        orders = orders.filter(province_name=province)
    query = request.GET.get("q", "").strip()
    if query:
        orders = orders.filter(
            Q(order_number__icontains=query) | Q(recipient__icontains=query)
        )

    context = {
        "orders": orders,
        "status_choices": OrderStatus.choices,
        "provinces": Order.objects.values_list("province_name", flat=True).distinct(),
        "active": "orders",
        "current_status": status,
        "current_province": province,
        "query": query,
    }
    return render(request, "dashboard/order_list.html", context)


@staff_required
def order_detail(request, number):
    """One order with its items, address and the status action buttons."""
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "history__changed_by"),
        order_number=number,
    )
    next_status, next_label = NEXT_ACTION.get(order.status, (None, None))
    context = {
        "order": order,
        "next_status": next_status,
        "next_label": next_label,
        "active": "orders",
        "can_cancel": order.status in services.ALLOWED_TRANSITIONS
        and OrderStatus.CANCELLED in services.ALLOWED_TRANSITIONS[order.status],
    }
    return render(request, "dashboard/order_detail.html", context)


@staff_required
def order_status(request, number):
    """Apply a status change chosen on the order detail page (POST only)."""
    if request.method != "POST":
        return redirect("dashboard:order_detail", number=number)
    order = get_object_or_404(Order, order_number=number)
    new_status = request.POST.get("new_status")
    note = request.POST.get("note", "")
    try:
        services.change_status(order, new_status, request.user, note=note)
        messages.success(request, f"Order {order.order_number} updated.")
    except (services.OrderError, KeyError, ValueError) as error:
        messages.error(request, str(error) or "That status change is not allowed.")
    return redirect("dashboard:order_detail", number=order.order_number)


# ---------- Products ----------

@staff_required
def product_list(request):
    """All products (active and inactive) with their variant counts."""
    products = (
        Product.objects.select_related("category")
        .prefetch_related("variants")
        .order_by("name")
    )
    return render(request, "dashboard/product_list.html", {"products": products, "active": "products"})


@staff_required
def product_form(request, pk=None):
    """Create or edit a product together with its variants and images.

    One page, three forms: the product form and the variant and image formsets.
    They all save together, so a half-saved product is never left behind.
    """
    product = get_object_or_404(Product, pk=pk) if pk else None

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        variants = VariantFormSet(request.POST, instance=product)
        images = ImageFormSet(request.POST, request.FILES, instance=product)
        if form.is_valid() and variants.is_valid() and images.is_valid():
            product = form.save()
            variants.instance = product
            variants.save()
            images.instance = product
            images.save()
            messages.success(request, f"Saved {product.name}.")
            return redirect("dashboard:product_list")
    else:
        form = ProductForm(instance=product)
        variants = VariantFormSet(instance=product)
        images = ImageFormSet(instance=product)

    context = {
        "form": form,
        "variants": variants,
        "images": images,
        "product": product,
        "active": "products",
    }
    return render(request, "dashboard/product_form.html", context)


# ---------- Inventory ----------

@staff_required
def inventory(request):
    """Every active variant with its stock, and a low-stock filter."""
    settings = StoreSettings.load()
    variants = (
        ProductVariant.objects.select_related("product", "size")
        .order_by("product__name", "size__sort_order")
    )
    low_only = request.GET.get("low") == "1"
    if low_only:
        variants = variants.filter(stock_qty__lte=settings.low_stock_threshold)
    context = {
        "variants": variants,
        "active": "inventory",
        "low_only": low_only,
        "threshold": settings.low_stock_threshold,
    }
    return render(request, "dashboard/inventory.html", context)


@staff_required
def inventory_adjust(request, pk):
    """Set a variant's stock to a new, non-negative number (POST only)."""
    if request.method != "POST":
        return redirect("dashboard:inventory")
    variant = get_object_or_404(ProductVariant, pk=pk)
    try:
        new_stock = int(request.POST.get("stock_qty", ""))
    except ValueError:
        new_stock = -1
    if new_stock < 0:
        messages.error(request, "Stock cannot be negative.")
    else:
        variant.stock_qty = new_stock
        variant.save(update_fields=["stock_qty"])
        messages.success(request, f"Updated stock for {variant.sku}.")
    return redirect("dashboard:inventory")


# ---------- Customers ----------

@staff_required
def customer_list(request):
    """Customers (non-staff users) with how many orders each has placed."""
    customers = (
        User.objects.filter(is_staff=False)
        .annotate(order_count=Count("orders"))
        .order_by("-date_joined")
    )
    return render(request, "dashboard/customer_list.html", {"customers": customers, "active": "customers"})


# ---------- Reviews ----------

@staff_required
def review_list(request):
    """All reviews, newest first, with a button to hide or show each one."""
    reviews = Review.objects.select_related("user", "product").order_by("-created_at")
    return render(request, "dashboard/review_list.html", {"reviews": reviews, "active": "reviews"})


@staff_required
def review_toggle(request, pk):
    """Hide a visible review or show a hidden one (POST only)."""
    if request.method != "POST":
        return redirect("dashboard:review_list")
    review = get_object_or_404(Review, pk=pk)
    review.is_visible = not review.is_visible
    review.save(update_fields=["is_visible"])
    messages.success(
        request,
        "Review shown." if review.is_visible else "Review hidden.",
    )
    return redirect("dashboard:review_list")
