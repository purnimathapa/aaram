# Phase 5: Staff dashboard

## What this phase built

The staff side of the store, all under `/staff/` and protected by one shared
check so only staff can reach it. Staff get a dashboard with KPI tiles and two
simple charts, an order list with filters and an order detail page where they
move an order through its statuses (or cancel it with a reason), a product
editor that saves a product with its variants and images together, an inventory
page with a quick stock adjust, and a read-only customer list.

## New and changed files

### Orders (status machine)
- `orders/services.py` - added `change_status(order, new_status, actor, note)`.
  It only allows the steps in `ALLOWED_TRANSITIONS`
  (Pending → Confirmed → Processing → Shipped → Delivered, and Cancelled from
  any step before Delivered). A cancel needs a reason and restores stock;
  delivering a Cash on Delivery order marks it Paid; every change writes a
  history row. The stock-restore code is shared with `cancel_order` via a small
  `_restore_stock` helper.

### Dashboard app
- `dashboard/permissions.py` - `staff_required`, the single decorator on every
  staff view. Visitors are sent to login; logged-in non-staff get 403.
- `dashboard/views.py` - one function per page, each with `@staff_required`:
  - `dashboard_home` - KPI tiles (pending orders, orders this period, sales from
    delivered orders, low-stock sizes), recent orders, the low-stock list, and
    two charts (orders per day, sales by province) built with ORM aggregation.
    A period filter (today / last 7 days / this month) changes what is counted.
  - `order_list` - all orders with status, province and number/customer filters.
  - `order_detail` + `order_status` - the order with its items, address and
    history, and the buttons that call `change_status` (cancel asks for a reason).
  - `product_list` + `product_form` - list all products; create or edit one
    together with its variant and image formsets, in a single save.
  - `inventory` + `inventory_adjust` - every variant with its stock, a low-stock
    filter, and a per-row form that sets the stock to a new, non-negative number.
  - `customer_list` - non-staff users with how many orders each has placed.
- `dashboard/forms.py` - `ProductForm` and the `VariantFormSet` (deactivate, do
  not delete) and `ImageFormSet` (deletable) inline formsets.
- `dashboard/urls.py` - the `/staff/...` routes.
- `dashboard/templates/dashboard/` - `base_staff.html` (staff header and nav)
  and the page templates.

### Shared
- `templates/base.html` - the header and footer are now in `{% block %}`s so the
  staff shell can replace the header with the staff nav and drop the public footer.
- `config/urls.py` - includes the dashboard at `/staff/`, and serves uploaded
  media in development so product images display.
- `static/js/staff.js` - submits a filter form when its select changes (the
  noscript Apply button is the fallback).
- `static/css/main.css` - the staff dashboard styles (header, KPI tiles, tables,
  CSS bar charts, forms), with a mobile layout.

## How to test it manually

1. `python manage.py createsuperuser`, then log in and open `/staff/` (or click
   nothing - a normal customer who visits `/staff/` gets a 403, and a logged-out
   visitor is sent to login).
2. On the dashboard, change the period and watch the KPI numbers and the charts
   change.
3. Open an order from the list. Move it forward step by step
   (Confirm → Start processing → Mark as shipped → Mark as delivered); once it is
   Delivered, a Cash on Delivery order shows as Paid. Try cancelling another order
   with a reason and check the product's stock goes back up.
4. Add a product with one variant and save; it appears in the catalogue. Edit it
   and deactivate a variant.
5. On Inventory, set a stock number; a negative number is refused. Use the
   "Show low stock only" filter.
6. Open Customers and confirm staff accounts are not listed and the order counts
   are right.

## Likely defense questions

1. **How is the staff area protected, and why one shared check?**
   Every staff view has the `@staff_required` decorator from
   `dashboard/permissions.py`. It wraps Django's `login_required` (so visitors go
   to login) and then checks `request.user.is_staff`, raising 403 for a logged-in
   customer. Keeping it in one place means no staff page can be left unprotected
   by accident, and the access tests check every URL.

2. **What stops a wrong status change, like Pending straight to Delivered?**
   `change_status` looks the current status up in `ALLOWED_TRANSITIONS` and
   refuses anything not listed, so only the correct next step (or a cancel) is
   allowed. Backward and skipped steps raise an `OrderError` that the view turns
   into a message.

3. **How does the product editor save a product with its sizes and photos at once?**
   The page has three forms: the `ProductForm` and two inline formsets
   (`VariantFormSet`, `ImageFormSet`). The view validates all three, saves the
   product, points each formset at it and saves them. Because it happens in one
   request they stay consistent, and variants are deactivated (is_active) rather
   than deleted so past orders still make sense.

4. **Where do the dashboard numbers come from - can they be faked from the browser?**
   They come from database queries: counts and `Sum`/`Count` aggregations over
   the orders and variants (for example sales are `Sum("total")` over delivered
   orders in the period). Nothing on the dashboard is read from the request
   except the period choice, so the figures cannot be tampered with.

5. **Why can inventory never go negative?**
   `inventory_adjust` reads the submitted number, and if it is missing, not a
   number, or below zero it refuses the change with a message and leaves the
   stock as it was. The `ProductVariant` model also has a database check that
   stock is at least zero, so even a bad write would be rejected.
