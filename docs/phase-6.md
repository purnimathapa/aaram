# Phase 6: Emails and reviews

## What this phase built

Two features from the Extras list. **Emails**: the store now sends a welcome
email when someone registers, a confirmation when an order is placed and a
notice when an order's status changes (password-reset emails were already handled
by Django). Each email is sent with `transaction.on_commit`, so it goes out only
once the change that triggered it is safely saved. **Reviews**: a customer can
rate and review a mattress, but only after an order of it has been delivered and
only once. The product page shows the average rating, the count and the reviews,
product cards show the average, and staff can hide a review without deleting it.

## New and changed files

### Emails
- `core/emails.py` - `send_welcome_email`, `send_order_placed_email` and
  `send_order_status_email`. Each renders a plain-text and an HTML template and
  sends with `transaction.on_commit`.
- `core/templates/emails/` - `welcome`, `order_placed`, `order_status` in
  `.txt` and `.html` (AARAM wordmark, no images).
- `accounts/views.py` - the register view sends the welcome email.
- `orders/services.py` - `place_order` sends the confirmation and
  `change_status` sends the status email, both inside the transaction (so they
  only fire on commit).
- `config/settings/base.py` - `DEFAULT_FROM_EMAIL`.
- `config/settings/prod.py` - SMTP settings from `.env` (dev still prints to the
  console).
- `.env.example` - the email variables (empty).

### Reviews
- `reviews/models.py` - `Review` (user, product, rating 1-5, title, body,
  is_visible, created_at), with one review per user per product and a rating
  check constraint.
- `reviews/services.py` - `can_review` (a delivered order with the product and
  no existing review), with `has_delivered_order` and `has_reviewed` helpers.
- `reviews/forms.py` - `ReviewForm` (rating as a 1-5 dropdown, title, body).
- `reviews/views.py` - `add_review`, POST only and login-required; it checks
  eligibility before saving and returns to the product page.
- `reviews/urls.py` - `/mattresses/<slug>/review/`.
- `reviews/admin.py` - a simple admin for reviews.
- `catalog/views.py` + `product_detail.html` - the product page now shows the
  average rating, the count, the reviews, and the review form for eligible users.
- `catalog/models.py` - `Product.review_summary` (average and count from the
  prefetched visible reviews) for the cards.
- `catalog/views.py`, `core/views.py`, `templates/partials/product_card.html` -
  listings prefetch reviews and the card shows the average.
- `dashboard/views.py`, `urls.py`, `base_staff.html`, `review_list.html` - a
  staff Reviews page to hide or show each review.

### Migration
- `reviews/migrations/0001_initial.py`.

## How to test it manually

1. Register a new account. In the terminal running `runserver` (console email
   backend) you will see the welcome email printed.
2. Place an order - a confirmation email is printed. As staff, move the order
   forward - a status email is printed for each change.
3. Reviews: as a customer, open a mattress you have **not** had delivered - there
   is no review form. Place an order for it and have staff mark it Delivered, then
   reopen the product - the review form appears. Submit a review; it shows on the
   page and in the average, and the card in the catalogue shows the rating. Try to
   review the same mattress again - you cannot.
4. As staff, open `/staff/reviews/` and hide the review; it disappears from the
   product page. Show it again and it returns.

## Likely defense questions

1. **Why send emails with `transaction.on_commit` instead of straight away?**
   An email about an order should only go out if the order was actually saved.
   `transaction.on_commit` runs the send after the surrounding transaction
   commits, so a checkout that rolls back (for example, the stock ran out) sends
   nothing. If there is no open transaction the send runs immediately. Our test
   wraps a `place_order` in a transaction that rolls back and checks no email was
   sent.

2. **Who is allowed to review a mattress, and how do you enforce it once?**
   `reviews.services.can_review` returns true only if the user has a Delivered
   order that contains the product and has not already reviewed it. The submit
   view checks this before saving, and the model has a
   `UniqueConstraint(user, product)` so the database also guarantees one review
   per product.

3. **How does the average rating on the product page and the cards stay efficient?**
   The product page averages the visible reviews with a single aggregate query.
   The cards use `Product.review_summary`, which reads the reviews that the list
   view already prefetched, so showing ratings for a page of products does not
   add a query per product.

4. **What does hiding a review do, and why not just delete it?**
   Hiding sets `is_visible` to false; the review stays in the database but is
   left out of the product page and the average. Keeping it means staff can show
   it again and there is a record, rather than losing it permanently.

5. **Where do the email settings live, and how does dev differ from production?**
   The "from" address is `DEFAULT_FROM_EMAIL` in base settings. Development uses
   the console backend (emails are printed), set in `dev.py`. Production uses the
   SMTP backend with host, port, user and password read from `.env`, set in
   `prod.py`, so no credentials are in the code.
