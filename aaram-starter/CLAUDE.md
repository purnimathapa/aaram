# AARAM: project instructions for Claude Code

AARAM is a Kathmandu University Year III / Semester II project: an e-commerce website for AARAM, a mattress brand that sells its **own** mattresses directly to customers across Nepal (not a retailer, no other brands). Five students must be able to explain every line at the defense, so clarity beats cleverness.

The full plan (scope, data model, URLs, phases, owners) is imported below. Follow it; ask before deviating.

@docs/BUILD_PLAN.md

## Stack (do not add to this without asking)
- Python 3.12, Django 5.2 LTS, PostgreSQL (psycopg 3)
- Django templates + one hand-written stylesheet (`static/css/tokens.css`, `static/css/main.css`) + small vanilla JS files
- django-environ, Pillow, requests, whitenoise, gunicorn
- No React/Vue, no REST API, no Bootstrap/Tailwind, no Celery, no Docker unless the team asks

## Commands
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # then fill in values locally
createdb aaram                       # PostgreSQL database
python manage.py migrate
python manage.py loaddata fixtures/*.json
python manage.py runserver
python manage.py test                # must pass before any phase is called done
```

In a cloud session (claude.ai/code): PostgreSQL 16 is installed but not running. Start it with `service postgresql start`, create the `aaram` database and a matching user, and use the available `python3` if 3.12 is not present. Never commit the `.env` file.

## How we work (one phase per session)
1. Work on exactly ONE phase from the build plan. Never start the next phase on your own.
2. Start in plan mode: read the relevant files, propose a plan (files to create/change, models, URLs, tests), wait for approval.
3. Work on a branch named `phase-N-short-name`. Commit in small, logical steps with clear messages.
4. Write tests with the feature, not after. Run `python manage.py test` and fix failures before finishing.
5. Finish each phase by writing `docs/phase-N.md`: what was built, every new file and what it does, how to test it manually, and 5 likely defense questions with answers.
6. End with a short summary and the manual checklist for the team. Do not merge to `main`; the team reviews and merges.

## Architecture rules
- Apps: `accounts`, `catalog`, `cart`, `orders`, `payments`, `reviews`, `dashboard`, `core`. Settings in `config/settings/` (`base.py`, `dev.py`, `prod.py`).
- Custom user model `accounts.User` (email login) must exist before the first migration.
- Business rules live in each app's `services.py` (e.g. `orders.services.place_order`, `orders.services.change_status`). Views stay thin: validate with a form, call a service, render or redirect.
- Use Django forms/ModelForms for all input. Use class-based views where they make code shorter; function views are fine for simple pages.
- Reuse template partials (`templates/partials/`) for header, footer, product card, form fields, messages.
- Staff pages live under `/staff/` and use one `StaffRequiredMixin`. Customer queries always filter by `request.user` (another user's order must 404).

## Data and business rules (never break these)
- Money is always `DecimalField(max_digits=10/12, decimal_places=2)`, never float. Prices are in NPR; display with Nepali grouping (Rs. 1,25,000) via a template filter.
- Price and stock live on `ProductVariant` (size + thickness). Add database `CheckConstraint`s: price > 0, stock_qty >= 0, quantity >= 1; `UniqueConstraint`s as listed in the plan.
- The server recalculates every price and total; never trust amounts from the browser.
- Checkout runs in `transaction.atomic()` with `select_for_update()` on the variants (ordered by id). Stock is reduced when the order is placed and restored when it is cancelled.
- `OrderItem` stores snapshots (product name, variant label, SKU, unit price); `Order` stores the delivery address snapshot.
- Status flow: Pending → Confirmed → Processing → Shipped → Delivered, or Cancelled. Customer may cancel only Pending; staff may cancel before Delivered with a reason. Every change writes `OrderStatusHistory`. Delivered COD orders become Paid.
- Khalti (sandbox): only a server-side `lookup` returning "Completed" with the right amount marks an order Paid. Never trust callback query parameters.
- Send emails with `transaction.on_commit`.
- Schema changes only through migrations. Never edit an applied migration; create a new one.

## Code style: simple, readable, no "vibe-coded" smell
- Follow Django conventions and PEP 8. Clear names over short names. Write the code a careful second-year student could read and defend.
- Write only what the current phase needs. No unused imports, functions, fields, settings, files or "future" hooks. No helper used once; no base classes or mixins with a single user (except `StaffRequiredMixin`).
- Comments explain *why* (locking, snapshots, status rules, security choices) in one or two plain sentences. No comments that restate the code, no banner comments, no TODOs left behind, no emoji anywhere.
- Each model, service function and non-obvious view gets a short docstring saying what it does and what it guarantees.
- No broad `try/except` that hides errors; catch the specific exception and handle it. No `print` debugging left in.
- Keep files focused: split a `views.py` or `services.py` that passes ~300 lines; one template per page, shared bits in `templates/partials/`.
- No secrets in code or Git: everything sensitive comes from `.env`; keep `.env.example` updated with empty values.
- Commit messages: imperative, specific ("Add stock check to place_order"), no emoji, no filler.

## Frontend and design
- Follow `docs/DESIGN.md` exactly (tokens, fonts, components, and the "not AI-looking" rules). The page mockups in `docs/design/mockups/` are the visual reference: match their layout, spacing and copy.
- CSS: `static/css/tokens.css` (custom properties only) and `static/css/main.css`, organised in commented sections (base, layout, components, pages). Use classes with plain names (`.product-card`, `.btn-primary`); no inline styles in templates, no CSS framework, no `!important`.
- JavaScript: small vanilla files in `static/js/`, one per behaviour (`variant-picker.js`, `province-map.js`), loaded only on pages that need them. Pages must still work for the core path without JS (forms submit normally).
- HTML: semantic elements, labelled inputs, alt text from the database, visible focus states, 44 px touch targets, works at 360 px wide.
- Graphics: inline SVG icons and CSS-drawn layer illustrations as in the mockups; real photos only from the team. Never stock "AI" imagery, never emoji.
