# Phase 4: Checkout and orders

## What this phase built

The customer side of ordering. From the cart a logged-in customer goes to
checkout, picks a delivery address, sees the subtotal, the province delivery
charge and the total, and places a Cash on Delivery order. Placing the order
runs in one safe database transaction that re-checks stock and prices, reduces
stock, stores snapshots and empties the cart. The customer gets a confirmation
page, can see all their orders and one order's detail with a status timeline,
and can cancel an order while it is still Pending (which puts the stock back).
Online payment and the staff order screens come in later phases; the Khalti
option here is shown but disabled.

## New and changed files

### Orders app
- `orders/models.py` - three models:
  - `Order` - the placed order. Holds the status, payment method and status,
    a **snapshot of the delivery address**, the subtotal, delivery charge and
    total, and the time. A database `CheckConstraint` guarantees
    `total = subtotal + delivery_charge`. `order_number` (e.g. `AR-2026-00042`)
    is built from the year and the order id right after it is saved.
  - `OrderItem` - one line, a **snapshot** of the variant (product name, size
    label, SKU, unit price) plus the quantity and line total. Constraints keep
    quantity at least 1 and `line_total = unit_price x quantity`.
  - `OrderStatusHistory` - one row per status change, for the timeline.
- `orders/services.py` - the two rules, each wrapped in `@transaction.atomic`:
  - `place_order(user, address, delivery_note, expected_subtotal)` - locks the
    cart's variants with `select_for_update()` (ordered by id to avoid
    deadlocks), re-checks each line is active and in stock, adds up the subtotal
    from the server's prices, refuses the order if the subtotal no longer matches
    what the customer saw or the province is not serviceable, then creates the
    order and items, reduces stock, writes the first history row and empties the
    cart. Raises `OrderError` with a clear message if anything is wrong.
  - `cancel_order(order, actor, reason="")` - only for a Pending order; sets it
    to Cancelled, puts each line's stock back and writes a history row.
- `orders/views.py` - all login-required; a customer only ever sees their own
  orders (`get_object_or_404(..., user=request.user)`):
  - `checkout` (GET) - address choice and the order summary.
  - `place` (POST only) - calls `place_order`, then redirects to the
    confirmation page (Post/Redirect/Get); on an `OrderError` it shows the
    message and returns to checkout.
  - `confirmation`, `order_list`, `order_detail` (with the timeline), and
    `cancel` (POST only).
  - `_build_timeline` turns the status and history into the steps shown on the
    order page (done / current / upcoming, or a Cancelled marker).
- `orders/urls.py` - `/checkout/`, `/checkout/place/`, `/orders/`,
  `/orders/<number>/`, `/orders/<number>/cancel/`, `/orders/<number>/confirmation/`.
- `orders/admin.py` - read-only admin so a superuser can inspect orders (the
  staff order screens are a later phase).
- `orders/templates/orders/` - `checkout.html`, `confirmation.html`,
  `order_list.html`, `order_detail.html`.
- `orders/tests.py` - the tests below.

### Shared
- `cart/templates/cart/cart.html` - the "Proceed to checkout" button now links
  to checkout.
- `accounts/templates/accounts/profile.html` - a "My orders" link.
- `static/js/checkout.js` - updates the delivery charge and total in the summary
  when the customer picks a different address, and blocks ordering to a province
  we do not serve. The page works without it (the server uses the chosen address).
- `static/css/main.css` - checkout, confirmation, order list and order detail
  styles, including the status pills and the timeline, with a mobile layout.

### Migration
- `orders/migrations/0001_initial.py`.

## How to test it manually

1. `python manage.py migrate`, then `python manage.py loaddata fixtures/*.json`.
2. Log in, add a mattress to the cart, open the cart and click **Proceed to
   checkout**.
3. On checkout, confirm the address, the delivery charge for its province and
   the total. Pick a different address (if you have one) and watch the delivery
   and total update. Place the order.
4. You land on the confirmation page with an order number like `AR-2026-00001`.
   The cart is now empty and the product's stock has gone down.
5. Open **My orders** from your profile, then the order: check the items,
   totals, address and the status timeline.
6. While the order is Pending, click **Cancel this order**. The status becomes
   Cancelled and the stock is restored (check the product page).
7. Edge cases: an empty cart or a province we do not serve stops checkout with a
   message; another customer's order number returns 404.

## Likely defense questions

1. **Walk through placing an order from the browser to the database.**
   The checkout form posts to `orders.views.place`, which loads the chosen
   address and calls `orders.services.place_order`. That function opens a
   transaction, locks the cart's variants, re-checks stock and recomputes the
   subtotal from the current prices, creates the `Order` and `OrderItem`
   snapshots, reduces stock, writes the first `OrderStatusHistory` row and
   clears the cart. The view then redirects to the confirmation page.

2. **Two people click "Place order" for the last mattress at the same time -
   what stops both succeeding?**
   `place_order` runs in `transaction.atomic()` and locks the variant rows with
   `select_for_update()`. The second checkout waits at that lock until the first
   commits, then reads the now-zero stock and is refused with an `OrderError`.
   Our concurrency test starts two threads at once and asserts exactly one order
   is created and stock ends at zero.

3. **Why store snapshots on the order and its items instead of just linking to
   the product and address?**
   Prices, products and addresses change over time. If we only linked to them,
   an old order would show today's price or a since-edited address. Copying the
   name, SKU, unit price and the address fields onto the order keeps the record
   true to the moment it was placed. The variant link is kept but nullable.

4. **How do you make sure the customer pays the right amount and cannot tamper
   with it?**
   The server never trusts amounts from the browser: it recomputes the subtotal
   from the locked variants' current prices and the delivery charge from the
   chosen address's province, and the `Order` has a database check that
   `total = subtotal + delivery_charge`. The hidden `expected_subtotal` only
   lets us detect a price change and ask the customer to look again.

5. **Who can cancel an order, and what happens to the stock?**
   A customer can cancel only while the order is Pending (`can_customer_cancel`),
   through a POST-only view that checks the order belongs to them. `cancel_order`
   sets the status to Cancelled, adds each line's quantity back to its variant's
   stock and records the change in the history. Later statuses can only be
   changed by staff, which is the next phase.
