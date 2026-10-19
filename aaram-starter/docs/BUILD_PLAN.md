# AARAM Build Plan

Django 5.2 + PostgreSQL, built in 10 phases over 16 weeks. Cash on Delivery comes first; Khalti sandbox payment, emails, reviews and deployment are added once the core works end to end.

## Scope

| Area | Customer can | Staff can | When |
| --- | --- | --- | --- |
| Accounts | Register, log in/out, reset password by email, edit profile, save Nepali addresses (province, district, municipality, ward, tole, landmark, phone) | Log in to staff area; see customer details for delivery | Core |
| Catalogue | Browse, search, filter (category, size, firmness, price, in stock), sort, product page with gallery, specs, size/thickness selector | Add/edit/deactivate products, variants (SKU, price, stock), images; manage categories and sizes | Core |
| Cart | Add a variant (login required), change quantity (max 5 per line), remove, see subtotal and stock warnings | — | Core |
| Checkout | Pick address, see province delivery charge and ETA, review summary, place COD order, confirmation with order number | — | Core |
| Orders | History, detail, status timeline; cancel while Pending | List/filter orders, move status forward, cancel with reason, mark COD paid on delivery | Core |
| Inventory and dashboard | "In stock" / "Only 2 left" / "Out of stock" per size | Adjust stock, low-stock list, order counts by status, sales totals, best sellers | Core |
| Store pages | Home, about, contact, delivery/warranty/return policy pages | Edit province delivery charges and store details (Django Admin) | Core |
| Online payment | Pay with Khalti (sandbox) instead of COD | See payment status and gateway reference | Extra |
| Email | Registration, order placed, status changes, password reset | — | Extra |
| Reviews | Rate (1–5) and review a mattress after delivery | Hide inappropriate reviews | Extra |
| Deployment | Use the live site on a public URL | — | Extra |

Out of scope: mobile app, live courier tracking, coupons, EMI, custom sizes, returns processing in the system. eSewa is a backup if Khalti's sandbox is unavailable.

## Project structure

```
aaram/
├── config/        # settings/base.py, dev.py, prod.py; urls.py; wsgi.py
├── accounts/      # User, Address, auth views, profile
├── catalog/       # Category, Size, Product, ProductImage, ProductVariant
├── cart/          # CartItem, cart views, context processor (cart count)
├── orders/        # Order, OrderItem, OrderStatusHistory, checkout + status services
├── payments/      # Payment, Khalti client, callback + verification
├── reviews/       # Review, eligibility rule
├── dashboard/     # staff-only pages (no models)
├── core/          # Province, StoreSettings, home + policy pages, emails, NPR filter
├── templates/     # base.html, partials/
├── static/        # css/tokens.css, css/main.css, js/
├── media/         # uploaded images (dev only, git-ignored)
├── fixtures/      # sample categories, sizes, provinces, products
├── docs/          # this plan, phase-N.md explainers
├── .env.example
├── requirements.txt
└── manage.py
```

## Data model (15 tables)

| Model (app) | Key fields | Rules and constraints |
| --- | --- | --- |
| User (accounts) | email (login), first/last name, phone, is_staff | Custom AbstractUser before first migration; email unique |
| Address (accounts) | user, province, recipient, phone, district, municipality, ward_no, street_tole, landmark, is_default | Nepali mobile format; ward ≥ 1; one default per user |
| Province (core) | name, delivery_charge, est_days_min/max, is_serviceable | 7 rows seeded; charge ≥ 0; min ≤ max |
| StoreSettings (core) | phone, email, address, low_stock_threshold, max_qty_per_line | Single row |
| Category (catalog) | name, slug, is_active | name and slug unique |
| Size (catalog) | name, length_in, width_in, sort_order | Name unique; dimensions > 0 |
| Product (catalog) | category, name, slug, description, material, firmness, warranty_months, is_active | Slug unique; deactivate, never delete once ordered |
| ProductImage (catalog) | product, image, alt_text, sort_order, is_primary | One primary per product |
| ProductVariant (catalog) | product, size, thickness_in, sku, price, stock_qty, is_active | SKU unique; (product, size, thickness) unique; price > 0; stock ≥ 0 |
| CartItem (cart) | user, variant, quantity | (user, variant) unique; quantity ≥ 1 |
| Order (orders) | order_number, user, status, payment_method, payment_status, address snapshot, subtotal, delivery_charge, total, placed_at | Number unique (AR-2026-00042); total = subtotal + delivery |
| OrderItem (orders) | order, variant (nullable), product_name, variant_label, sku, unit_price, quantity, line_total | Snapshots; line_total = unit_price × quantity |
| OrderStatusHistory (orders) | order, from_status, to_status, changed_by, note, changed_at | One row per change |
| Payment (payments) | order, provider, pidx, amount, status, raw_response, created/updated | One row per attempt; only verified "Completed" marks Paid |
| Review (reviews) | user, product, rating, title, body, is_visible, created_at | (user, product) unique; rating 1–5; only after a Delivered order |

## Key flows

**Checkout (`orders/services.py → place_order`)**
1. Redirect to login if needed, to cart if empty.
2. Customer picks an address; province gives delivery charge and ETA (blocked if not serviceable).
3. Server builds the summary from current prices and stores a fingerprint in the form.
4. On confirm: `transaction.atomic`, lock cart variants with `select_for_update()` in id order.
5. Check active + enough stock + total matches fingerprint; otherwise roll back and show what changed.
6. Create Order + OrderItems (snapshots), reduce stock, first status-history row, empty cart, commit.
7. Redirect to confirmation (Post/Redirect/Get).

**Khalti sandbox (`payments/`)**
1. `place_order` runs as above with payment status Unpaid.
2. Server calls Khalti `initiate` (sandbox base `https://dev.khalti.com/api/v2/`) with order number and amount in paisa; redirect to `payment_url`.
3. Khalti returns the customer to our callback with `pidx`.
4. Server calls Khalti `lookup`; only "Completed" with matching amount marks Payment completed and Order Paid.
5. Failed/abandoned: order stays Pending/Unpaid, customer can retry. Management command `expire_unpaid_orders` cancels unpaid online orders after 30 minutes and restores stock.

**Order statuses (`orders/services.py → change_status`)**: Pending → Confirmed → Processing → Shipped → Delivered; Cancelled from Pending (customer or staff) or Confirmed/Processing/Shipped (staff only, reason required). Cancel restores stock; Delivered sets COD to Paid; every change writes a history row.

**Emails (`core/emails.py`)**: welcome, order placed, status change, password reset; sent with `transaction.on_commit`; console backend in dev, SMTP from `.env` in production.

**Reviews (`reviews/`)**: only customers with a Delivered order containing the product, once per product; product page shows average rating and count; staff can hide.

## Pages and URLs

| URL | Page | Access |
| --- | --- | --- |
| `/` | Home | Public |
| `/mattresses/` | Catalogue: search, filters, sort, pagination | Public |
| `/mattresses/<slug>/` | Product page: gallery, size/thickness picker, specs, reviews | Public |
| `/about/`, `/contact/`, `/policies/<delivery|warranty|returns>/` | Store and policy pages | Public |
| `/accounts/register/`, `login/`, `logout/`, `password-reset/…` | Authentication | Public |
| `/accounts/profile/` | Profile, change password | Customer |
| `/accounts/addresses/` (+ add, edit, delete) | Address book | Customer |
| `/cart/` (+ add, update, remove) | Cart | Customer |
| `/checkout/`, `/checkout/confirm/` | Address, summary, place order | Customer |
| `/orders/`, `/orders/<number>/`, `/orders/<number>/cancel/` | History, detail + timeline, cancel | Customer |
| `/orders/<number>/pay/`, `/payments/khalti/callback/` | Khalti start and return | Customer |
| `/mattresses/<slug>/review/` | Write a review | Customer (eligible) |
| `/staff/` | Dashboard: KPIs, recent orders, low stock | Staff |
| `/staff/products/` (+ new, edit) | Products with variant and image formsets | Staff |
| `/staff/inventory/` | Stock per variant, quick adjust, low-stock filter | Staff |
| `/staff/orders/`, `/staff/orders/<number>/` | Order list and detail with status actions | Staff |
| `/staff/customers/`, `/staff/reviews/` | Customers; hide/show reviews | Staff |
| `/admin/` | Django Admin: categories, sizes, provinces, settings, staff users | Superuser |

## Build phases

| Phase | Weeks | What we build | Done when |
| --- | --- | --- | --- |
| 0. Setup | 1 | Repo, Django project, PostgreSQL, `.env`, settings split, custom User, base template, design tokens, test runner | Fresh clone runs `migrate` + `runserver`; one test passes |
| 1. Accounts | 2–3 | Register, login/logout, password reset (console email), profile, address book, 7 provinces seeded | New user signs up, adds address, logs back in; login-required tests |
| 2. Catalogue | 4–6 | Catalogue models + admin, fixtures, home, catalogue (search/filter/sort/pagination), product page with variant picker | 6+ sample mattresses; price and stock change with selected variant |
| 3. Cart | 7 | Add/update/remove, max per line, stock warnings, header cart count | Cart survives logout/login; over-stock quantity refused |
| 4. Checkout and orders | 8–9 | `place_order`, confirmation, history, detail + timeline, customer cancel | End-to-end COD order; two buyers of last unit → exactly one succeeds |
| 5. Staff dashboard | 10–11 | Product form with formsets, inventory, order list/detail with status actions, KPIs, customers | Staff runs an order Pending → Delivered; customers blocked from `/staff/` |
| 6. Emails and reviews | 12 | Email templates/sending; review form, eligibility, average rating | Emails for each event; only delivered buyers can review |
| 7. Khalti payment | 13 | Payment model, initiate, callback, lookup, retry, unpaid expiry | Sandbox payment marks Paid; tampered callback does not |
| 8. Testing and polish | 14 | Full tests, responsive + accessibility check, security settings, sample data/photos | All tests green; checklist passes |
| 9. Deploy and defend | 15–16 | Hosting, managed PostgreSQL, media storage, README, demo script | Public URL works end to end; everyone can demo their module |

Gate: phases 6–9 start only after phase 5 is done. If a core phase slips, cut Khalti first, then reviews, then emails.

## Module ownership

| Member | Owns | Explains at the defense |
| --- | --- | --- |
| Suyesh Ghimire | `accounts`, `core/emails` | Custom user model, auth, password hashing, CSRF, address validation, email on commit |
| Romin Manandhar | `catalog` | Product–variant–size design, migrations, search/filter queries, variant picker JS, uploads |
| Pratyush Pokharel | `cart`, `orders` (customer side) | Checkout transaction, row locking, snapshots, statuses, concurrency test |
| Rajak Shingkhwal | `dashboard` | Staff authorization, formsets, inventory adjustments, KPI aggregation queries |
| Purnima Thapa | `payments`, `reviews`, test lead | Khalti initiate/lookup and why callbacks aren't trusted, review eligibility, test suite |

## Tests we must have
- Constraints: negative stock, zero price, duplicate SKU, duplicate cart line rejected by the database
- Permissions: visitors redirected from cart/checkout; another customer's order → 404; customers blocked from `/staff/`
- Checkout: server recalculates totals; price change between summary and confirm caught; stock decreases; cart empties; snapshots stored
- Concurrency: two parallel checkouts for the last unit → exactly one succeeds
- Status rules: allowed transitions pass, skipped/backward fail; cancel restores stock; Delivered sets COD Paid
- Payments: mocked `lookup` "Completed" marks Paid; "Pending", wrong amount or forged callback does not
- Reviews: only delivered buyers, once per product
