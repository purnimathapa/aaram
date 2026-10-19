# AARAM prompts for Claude Code

Use one new conversation per phase. In the VS Code extension, open the Claude Code panel, start a new conversation, switch to **Plan mode** before sending the phase prompt, read the plan, ask questions, then approve. In the terminal: `claude --permission-mode plan`. On claude.ai/code: choose **Plan** in the mode menu.

Every prompt below assumes `CLAUDE.md`, `docs/BUILD_PLAN.md`, `docs/DESIGN.md` and `docs/design/mockups/` are in the repo.

---

## Phase 0: Setup

```
Start Phase 0 (Setup) from docs/BUILD_PLAN.md. Read CLAUDE.md and docs/DESIGN.md first.

Build the project skeleton only:
- requirements.txt: Django 5.2, psycopg[binary] 3, django-environ, Pillow, requests, whitenoise, gunicorn (pinned versions)
- config/ with settings/base.py, dev.py, prod.py; read SECRET_KEY, DEBUG, DATABASE_URL, ALLOWED_HOSTS from .env; TIME_ZONE Asia/Kathmandu; .env.example with empty values; .gitignore (.venv, .env, media/, __pycache__)
- the eight apps from the plan, registered, each nearly empty
- accounts.User (AbstractUser, unique email used as the login field, phone) as AUTH_USER_MODEL before the first migration; register it in admin
- templates/base.html with partials/header.html, partials/footer.html, partials/messages.html, matching docs/design/mockups/Main.dc.html header and footer
- static/css/tokens.css (all tokens from docs/DESIGN.md) and static/css/main.css (base, layout, buttons, header, footer sections)
- core: a simple home page view and template that renders the header, a short hero and the footer
- one test: the home page returns 200 and uses base.html
- README.md: macOS setup with Homebrew, python@3.12, postgresql@16, venv, createdb, migrate, runserver, test

Do not add anything the plan does not need yet. Propose the plan first and wait for my approval. Then work on branch phase-0-setup, commit in small steps, run the tests, and write docs/phase-0.md.
```

## Phase 1: Accounts

```
Start Phase 1 (Accounts) from docs/BUILD_PLAN.md. Read CLAUDE.md, docs/DESIGN.md and docs/phase-0.md first.

Build:
- registration (first name, last name, email, phone, password twice), login with email, logout (POST only), password reset using Django's built-in views with the console email backend in dev, password change, profile edit
- core.Province model (name, delivery_charge, est_days_min, est_days_max, is_serviceable) with constraints from the plan, admin, and a fixture of the 7 provinces with clearly sample charges
- accounts.Address model with the Nepali fields, Nepali mobile number validation, ward >= 1, one default address per user (partial unique constraint), and address book pages (list, add, edit, delete) that only show the logged-in user's addresses
- forms styled per docs/DESIGN.md (labels above fields, plain error text)
- tests: login required for profile and addresses, another user's address returns 404, only one default address, phone validation

Plan first and wait for approval. Branch phase-1-accounts. Finish with docs/phase-1.md.
```

## Phase 2: Catalogue

```
Start Phase 2 (Catalogue) from docs/BUILD_PLAN.md. Read CLAUDE.md, docs/DESIGN.md, the mockups Main, Catalogue and Product in docs/design/mockups/, and earlier docs/phase-*.md.

Build:
- Category, Size, Product, ProductImage, ProductVariant with every constraint and index from the plan; admin with variant and image inlines
- fixtures: 4 sizes (Single 72x36, Double 72x48, Queen 75x60, King 78x72), 4 categories, 6 sample AARAM mattresses with 6 in and 8 in variants, prices and stock (marked as sample data)
- core template filter `npr` that formats numbers with Nepali grouping (Rs. 1,25,000) with a unit test
- home page sections from the Main mockup: hero with layer illustration, trust row, shop by feel, popular mattresses, size guide drawn to scale, how ordering works
- catalogue page from the Catalogue mockup: search (name, category, material), filters (category, size, firmness, price range, in stock), sort, pagination (12 per page), filters kept in the URL query string
- product page from the Product mockup: layer illustration, size and thickness chips, price and stock that update with the selection (static/js/variant-picker.js, with a no-JS fallback form), specs list, delivery box
- the product card and layer illustration as reusable partials
- efficient queries (select_related / prefetch_related); tests for filters, search, inactive products hidden, npr filter

Plan first and wait for approval. Branch phase-2-catalogue. Finish with docs/phase-2.md.
```

## Phase 3: Cart

```
Start Phase 3 (Cart) from docs/BUILD_PLAN.md. Read CLAUDE.md, docs/DESIGN.md and earlier docs/phase-*.md.

Build:
- cart.CartItem (user, variant, quantity) with the unique and check constraints from the plan
- core.StoreSettings single-row model with low_stock_threshold and max_qty_per_line (default 5), editable in admin
- cart services: add_to_cart, update_quantity, remove_item, each validating stock and the per-line maximum
- POST-only views for add/update/remove (login required; visitors are sent to login and back to the product page)
- cart page: lines with layer thumbnail, variant label, unit price, quantity control, line total, subtotal, stock warnings, inactive variants removed with a message
- header cart count through a context processor
- tests: login required, quantity above stock or above 5 refused, duplicate line merges, cart survives logout/login

Plan first and wait for approval. Branch phase-3-cart. Finish with docs/phase-3.md.
```

## Phase 4: Checkout and orders

```
Start Phase 4 (Checkout and orders) from docs/BUILD_PLAN.md. Read CLAUDE.md, docs/DESIGN.md, the Checkout and OrderDetail mockups, and earlier docs/phase-*.md.

Build:
- Order, OrderItem, OrderStatusHistory exactly as in the plan (snapshots, totals check constraint, human-readable order_number AR-YYYY-NNNNN)
- orders/services.py:
  - place_order(user, address, payment_method, expected_total): transaction.atomic, select_for_update on the cart variants ordered by id, re-check active/stock/total, create order and items with snapshots, reduce stock, first history row, clear cart; raise a clear exception listing what changed if a check fails
  - change_status(order, new_status, actor, note=""): allowed transitions only, customer may cancel only Pending, staff cancel needs a note, cancel restores stock, Delivered sets COD payment to Paid, always writes history
- checkout page from the Checkout mockup: choose address (or add one), province delivery charge and ETA, summary with a total fingerprint, Cash on Delivery selected (Khalti option shown but disabled until Phase 7), place order with Post/Redirect/Get to a confirmation page
- My orders list and order detail with the status timeline from the OrderDetail mockup; customer cancel button only while Pending
- tests: totals recalculated server-side, price change between summary and confirm is caught, insufficient stock blocks the order, stock decreases, cart empties, snapshots stored, another user's order 404, all status transition rules, and a concurrency test where two checkouts race for the last unit and exactly one succeeds (TransactionTestCase with threads)

Plan first and wait for approval. Branch phase-4-checkout. Finish with docs/phase-4.md.
```

## Phase 5: Staff dashboard

```
Start Phase 5 (Staff dashboard) from docs/BUILD_PLAN.md. Read CLAUDE.md, docs/DESIGN.md, the Dashboard mockup and earlier docs/phase-*.md.

Build under /staff/ with one StaffRequiredMixin:
- dashboard from the mockup: KPI tiles (pending orders, orders this period, sales from delivered orders, low-stock sizes), recent orders table with the next action, low-stock list, orders-per-day and sales-by-province bar charts computed with ORM aggregation (CSS bars or Chart.js loaded only on this page), period filter (today, 7 days, this month)
- orders list with filters (status, date, province, search by order number or customer) and order detail with status action buttons that call change_status (cancel asks for a reason)
- products list, product create/edit with variant and image formsets, deactivate instead of delete
- inventory page: every variant with stock, inline stock adjust form, low-stock filter
- customers list (read-only) with their order count
- tests: every /staff/ URL refuses customers and visitors, status actions follow the rules, stock adjust cannot go negative, KPI numbers match the data

Plan first and wait for approval. Branch phase-5-dashboard. Finish with docs/phase-5.md.
```

## Phase 6: Emails and reviews

```
Start Phase 6 (Emails and reviews) from docs/BUILD_PLAN.md. Read CLAUDE.md, docs/DESIGN.md and earlier docs/phase-*.md.

Build:
- core/emails.py with simple HTML + plain-text templates (AARAM wordmark, no images) for: welcome, order placed, status changed, password reset; sent through transaction.on_commit; console backend in dev, SMTP settings from .env in prod
- reviews.Review (user, product, rating 1-5, title, body, is_visible, created_at) with the unique constraint; eligibility service (customer has a Delivered order containing the product and no review yet); review form on the product page; average rating and count on product page and cards; staff hide/show page under /staff/reviews/
- tests: emails sent only after commit, ineligible users cannot review, one review per product, hidden reviews not shown

Plan first and wait for approval. Branch phase-6-emails-reviews. Finish with docs/phase-6.md.
```

## Phase 7: Khalti payment (sandbox)

```
Start Phase 7 (Khalti sandbox) from docs/BUILD_PLAN.md. Read CLAUDE.md, the Khalti flow in the plan, and earlier docs/phase-*.md. Check Khalti's current ePayment docs before writing the client.

Build:
- payments.Payment (order, provider, pidx, amount, status, raw_response, timestamps)
- payments/khalti.py: a small client with initiate() and lookup() using requests, base URL and secret key from .env, amounts in paisa
- enable Khalti at checkout: place_order as usual, then initiate and redirect to payment_url; callback view reads pidx, calls lookup, and only "Completed" with the matching amount marks the payment completed and the order Paid; otherwise show a clear message and a retry button on the order page
- management command expire_unpaid_orders: cancels unpaid Khalti orders older than 30 minutes using change_status (restores stock)
- tests with lookup mocked: Completed marks paid, Pending/failed/wrong amount do not, forged callback parameters are ignored, expiry restores stock

Plan first and wait for approval. Branch phase-7-khalti. Finish with docs/phase-7.md.
```

## Phase 8: Testing and polish

```
Start Phase 8 (Testing and polish). Read CLAUDE.md, docs/DESIGN.md, docs/BUILD_PLAN.md ("Tests we must have") and all docs/phase-*.md.

1. Compare the test suite with "Tests we must have" and add what is missing.
2. Review the whole codebase against CLAUDE.md's code style and DESIGN.md's "not AI-looking" rules; list problems first, then fix them: dead code, unused imports, duplicated logic, comments that restate code, inline styles, inconsistent spacing or colours, missing alt text or labels.
3. Check every page at 360, 768 and 1280 px and with keyboard only; fix layout and focus problems.
4. Run python manage.py check --deploy with prod settings and fix the warnings.
Show me the problem list before changing anything. Branch phase-8-polish. Finish with docs/phase-8.md.
```

## Phase 9: Deploy and defend

```
Start Phase 9 (Deploy). Read CLAUDE.md and docs/BUILD_PLAN.md.
1. Compare current options for hosting a Django + PostgreSQL app with uploaded images on a student budget; give me 2-3 options with cost and limits, and wait for my choice.
2. Then prepare production: prod settings, whitenoise, gunicorn, managed PostgreSQL, media storage, SMTP, Khalti sandbox keys, a deployment section in README.
3. Write docs/demo-script.md: a 10-minute defense demo (customer journey, staff journey, Khalti sandbox, review, PostgreSQL tables, test run) with who presents which part.
Branch phase-9-deploy.
```

---

## Prompts to use after every phase

**Clean-code review (run before merging):**
```
Review the changes on this branch against CLAUDE.md and docs/DESIGN.md as a strict reviewer. List: unused or duplicated code, anything more complex than needed, missing or useless comments, missing tests, security problems, and anything that looks AI-generated in the UI or code. Do not change anything yet; give me the list ranked by importance.
```

**Understand it for the defense (run as the module owner):**
```
Explain this phase to me as if I have to defend it tomorrow. Walk through the request from the browser to the database for the main feature, file by file, then ask me 5 questions and check my answers.
```

**Match the mockup:**
```
Compare the page at <URL> with docs/design/mockups/<Name>.dc.html. List every visual difference (layout, spacing, type, colour, copy), then fix them using only classes in main.css and the tokens in tokens.css.
```

**Fix a bug:**
```
When I do <steps>, I expect <expected> but get <actual>. Here is the full error: <paste>. Find the cause before changing code, explain it in two sentences, then fix it and add a test that would have caught it.
```
