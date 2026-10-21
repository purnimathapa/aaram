# Phase 3: Cart

## What this phase built

A database-backed shopping cart for logged-in customers. From a product page
a customer picks a size and thickness and adds it to the cart; the cart page
lists the lines with their price, lets the customer change the quantity or
remove a line, and shows the subtotal. A count badge in the header reflects the
cart on every page. Stock and a per-line maximum are enforced in one place so
the same rules cover the product page, the cart and the tests. Delivery and
checkout are not part of this phase; the checkout button is a placeholder.

## New and changed files

### Cart app
- `cart/models.py` - `CartItem` (user, variant, quantity, added_at). A
  `UniqueConstraint(user, variant)` keeps a variant on a single line, and a
  `CheckConstraint(quantity >= 1)` keeps quantities positive. A `line_total`
  property returns price x quantity at the variant's current price.
- `cart/services.py` - the cart rules, called by the views:
  - `add_to_cart(user, variant, quantity)` - adds a variant, merging with an
    existing line; refuses an inactive or out-of-stock variant and anything over
    the variant's stock or the store's per-line maximum.
  - `update_quantity(item, quantity)` - sets a line to an exact quantity within
    the same limits.
  - `remove_item(item)` and `cart_lines(user)` (lines with their variants loaded).
  - `CartError` - raised when a rule is broken; the view turns it into a message.
- `cart/views.py` - `cart_detail` (GET) renders the cart, drops any line whose
  variant was deactivated, and builds each line's stock warning and quantity
  choices. `add`, `update` and `remove` are POST-only and login-required; they
  call a service, add a message and redirect (Post/Redirect/Get). `update` and
  `remove` look up the line by both pk and `user`, so one customer cannot touch
  another's cart.
- `cart/urls.py` - `/cart/`, `/cart/add/`, `/cart/<pk>/update/`, `/cart/<pk>/remove/`.
- `cart/context_processors.py` - `cart_count` adds the total quantity in the
  current user's cart to every template (0 when logged out).
- `cart/templates/cart/cart.html` - the cart page: line items (thumbnail,
  name, variant, unit price, warning), a quantity select, line total, a remove
  button, and the summary with the subtotal.
- `cart/tests.py` - the tests below.

### Core
- `core/models.py` - `StoreSettings`, a single row (use `StoreSettings.load()`)
  holding `low_stock_threshold` and `max_qty_per_line` (default 5), editable in
  the admin as one record (no add or delete).
- `core/admin.py` - registers `StoreSettings`.

### Catalog
- `catalog/models.py` - `Product.get_absolute_url()` so the cart and other
  pages can link to a product without repeating the URL name.
- `catalog/views.py` - the product page now passes each variant's id and the
  store's `max_qty_per_line` so the add-to-cart form can post a variant.
- `catalog/templates/catalog/product_detail.html` - an add-to-cart form
  (variant + quantity) for logged-in customers; logged-out visitors see a
  "Log in to add to cart" link that returns to the product page.

### Shared
- `templates/partials/header.html` - the cart icon links to the cart and shows
  the count badge.
- `static/js/variant-picker.js` - as the shopper changes size or thickness it
  now also updates the hidden variant id, caps the quantity to the stock, and
  enables or disables the add-to-cart button.
- `static/js/cart.js` - submits a line's quantity form when the number changes,
  so no separate Update button is needed (a noscript button is the fallback).
- `static/css/main.css` - add-to-cart and cart-page styles, including the
  mobile layout.

### Migrations
- `cart/migrations/0001_initial.py`, `core/migrations/0002_storesettings.py`.

## How to test it manually

1. `python manage.py migrate`, then `python manage.py loaddata fixtures/*.json`.
2. Register or log in, open a mattress, pick a size and thickness, and click
   **Add to cart**. The header count goes up and the cart page shows the line.
3. Add the same size again - the quantity merges into one line, it does not
   create a second.
4. Try to set a quantity above the stock or above 5 - it is refused with a
   message.
5. Change a quantity and remove a line; the subtotal and the header count
   follow.
6. Log out and back in - the cart is still there (it belongs to the user).
7. As a logged-out visitor, the product page shows "Log in to add to cart" and
   `/cart/` sends you to the login page.
8. Turn JavaScript off: the quantity select shows an Update button, and adding
   to cart still works after choosing a size with "Show price for this size".

## Likely defense questions

1. **Where does the cart live, and why in the database rather than the session?**
   Each line is a `CartItem` row tied to the user. A database cart follows the
   customer between devices and survives logging out and back in, and it lets
   the server lock and check stock at checkout. We require login to add to the
   cart, so there is always a user to attach it to.

2. **How do you stop a customer ordering more than you have, or an absurd quantity?**
   Both limits are checked in `cart/services.py`, not in the view or template.
   A line may not exceed the variant's `stock_qty` or the store's
   `max_qty_per_line` (default 5, in `StoreSettings`), on add and on update. The
   model also has a database `CheckConstraint` that quantity is at least 1.

3. **What happens when the same size is added twice?**
   `add_to_cart` finds the existing line and increases its quantity instead of
   creating a duplicate, and the `UniqueConstraint(user, variant)` guarantees at
   the database level that a variant appears at most once per cart.

4. **Why are add, update and remove POST-only, and how is one customer kept out
   of another's cart?**
   They change data, so they must not run from a GET (a link, a prefetch or a
   refresh); `require_POST` enforces that and the forms carry the CSRF token.
   `update` and `remove` fetch the line with `get_object_or_404(..., user=request.user)`,
   so another customer's line id returns 404.

5. **What if a variant sells out or is withdrawn after it is in the cart?**
   The cart page drops any line whose variant is no longer active and tells the
   customer. If stock has merely dropped below the quantity, the line shows a
   warning to reduce it; the final, authoritative check happens inside the
   checkout transaction in the next phase.
