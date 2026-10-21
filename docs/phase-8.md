# Phase 8: Testing and polish

## What this phase did

A check-and-tidy pass over the whole project before deployment: filled the gaps
in the test suite against the "Tests we must have" list, added the production
security settings so `manage.py check --deploy` is clean, removed unused imports,
and improved a few accessibility details. No features were added or changed.

## Test coverage review

The suite was compared with the "Tests we must have" list in the build plan.
Most items were already covered by earlier phases; the gap was the
database-level constraint tests, now added:

- `catalog/tests.py::VariantConstraintTests` - the database rejects a zero price,
  negative stock and a duplicate SKU.
- `cart/tests.py::CartConstraintTests` - the database rejects a duplicate cart
  line for the same user and variant.

Already covered in earlier phases (for reference):

| Must-have test | Where |
| --- | --- |
| Permissions: cart/checkout need login; another user's order 404; customers blocked from /staff/ | `cart`, `orders`, `dashboard` |
| Checkout recalculates totals; price change caught; stock drops; cart empties; snapshots | `orders.CheckoutServiceTests` |
| Concurrency: two buyers, last unit, one wins | `orders.CheckoutConcurrencyTest` |
| Status rules: allowed pass, skipped/backward fail; cancel restores stock; delivered COD Paid | `orders.ChangeStatusTests` |
| Payments: lookup Completed marks paid; Pending/wrong amount/forged do not | `payments` |
| Reviews: only delivered buyers, once per product; hidden not shown | `reviews` |

The suite is **103 tests**, all passing.

## Code tidy

- Removed unused imports found by pyflakes across the apps (test modules and one
  view import).
- Confirmed there is no leftover debug code (`print`, `console.log`, `TODO`).

## Security (deploy check)

`config/settings/prod.py` now sets the hardening Django recommends for a live
HTTPS site: `SECURE_SSL_REDIRECT`, the proxy SSL header, secure session and CSRF
cookies, one year of HSTS (with subdomains and preload), content-type nosniff and
`X_FRAME_OPTIONS = "DENY"`. With these,

```
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy
```

reports no issues once a real (long, random) `SECRET_KEY` is set in `.env`.

## Accessibility and responsive

- The staff order filters (search box and the status/province selects) now have
  `aria-label`s, so every control has an accessible name.
- Public forms already use real `<label>`s, inputs have visible focus rings (set
  in the base styles), and touch targets are at least 44 px.
- Layouts were reviewed at phone width: the stylesheet collapses the multi-column
  pages (cart, checkout, order detail, dashboard) to a single column and lets wide
  staff tables scroll sideways at 640 px and below; the fluid grids hold up at
  tablet and desktop widths.

## Likely defense questions

1. **How do you know the database, not just the forms, enforces the rules?**
   Beyond the form and service checks, there are database `CheckConstraint`s and
   `UniqueConstraint`s on the models, and `VariantConstraintTests` /
   `CartConstraintTests` prove them by creating bad rows inside a transaction and
   asserting the database raises `IntegrityError`.

2. **What did you harden for production, and how do you check it?**
   `prod.py` forces HTTPS, marks cookies secure, turns on HSTS and the nosniff and
   anti-framing headers. `manage.py check --deploy` with the production settings
   confirms there are no remaining security warnings.

3. **Why keep development on plain HTTP if production forces HTTPS?**
   Local development has no certificate, so forcing HTTPS would make the site
   unreachable. The secure settings live only in `prod.py`; `dev.py` keeps the
   defaults, which is why the split settings matter.
