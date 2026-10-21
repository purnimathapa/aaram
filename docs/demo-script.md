# AARAM defense demo script

A ten-minute walkthrough of the live site, with who presents each part. Owners
match the build plan. Have two browser profiles open: one normal customer and
one staff member (and the Django admin in a third tab). Seed sample data first
(`loaddata fixtures/*.json`) and create one staff user.

Keep a mattress with low stock ready so the "Only N left" and the concurrency
story are visible.

## 0. Setup before the panel arrives (1 min, whole team)

- Live URL open on the home page.
- A customer account logged in on profile 1; a staff account ready on profile 2.
- The Django admin open on `/admin/` in a third tab.
- A terminal ready to run the test suite.

## 1. Customer journey — browse to cart (2 min) — Romin (catalogue)

1. Home page: hero, shop by feel, popular mattresses, size guide.
2. Go to the catalogue. Show search, a filter (size or firmness), sort, and the
   page count. Point out the price and the "In stock / Only N left" labels.
3. Open a product. Change size and thickness and show the price and stock update
   live (and that it still works without JavaScript). Show the specs.
4. Add a size to the cart; the header count updates.

## 2. Accounts and addresses (1 min) — Suyesh (accounts)

1. On the cart, click Checkout; show that a visitor is sent to login (log in).
2. Open the profile and the address book; show a saved Nepali address
   (province, district, municipality, ward, tole) and the one-default rule.

## 3. Checkout and the order (2 min) — Pratyush (cart and orders)

1. Checkout: choose the address, show the province delivery charge and the total
   updating, and the "we recheck price and stock" note.
2. Place a Cash on Delivery order. Land on the confirmation page with the order
   number (AR-YYYY-NNNNN).
3. Open My orders and the order detail with the status timeline.
4. One sentence on safety: placing an order locks the stock rows and rechecks
   everything in one transaction, so two people cannot both buy the last unit
   (the concurrency test proves it).

## 4. Khalti payment (sandbox) (1.5 min) — Purnima (payments)

1. Place a second order choosing **Khalti**; go to the Khalti sandbox and pay.
2. Return to the site: the order shows **Paid**.
3. Key point: we mark the order Paid only after our server asks Khalti (lookup)
   and gets "Completed" for the exact amount - never from the return URL, which
   could be forged.

## 5. Staff journey (2 min) — Rajak (dashboard)

1. Log in as staff and open `/staff/`. Show the KPI tiles and the two charts
   (orders per day, sales by province), and that the numbers come from the
   database.
2. Open the order from step 3 and move it forward: Confirm -> Processing ->
   Shipped -> Delivered. Point out the COD order becomes Paid on delivery.
3. Open Inventory and adjust a stock number (show a negative value is refused).
4. Show Products: a product with its variant and image formsets.

## 6. Reviews (0.5 min) — Purnima (reviews)

1. As the customer whose order was delivered, open that product and leave a
   review; show it appears with the average, and that only a delivered buyer can
   review, once.
2. As staff, open `/staff/reviews/` and hide the review; it disappears from the
   shop.

## 7. Under the hood (1 min) — Suyesh + Purnima

1. In the Django admin, show the PostgreSQL-backed tables: users, products and
   variants, orders with their items and status history, payments, reviews.
2. In the terminal run `python manage.py test` and show the suite passing
   (constraints, permissions, checkout, concurrency, status rules, payments,
   reviews).

## Who answers what

| Area | Owner |
| --- | --- |
| Accounts, auth, addresses, emails | Suyesh Ghimire |
| Catalogue, variants, search/filter, uploads | Romin Manandhar |
| Cart, checkout, orders, concurrency | Pratyush Pokharel |
| Staff dashboard, formsets, KPIs | Rajak Shingkhwal |
| Khalti payment, reviews, the test suite | Purnima Thapa |

## If something fails live

- Keep screenshots or a short screen recording of each step as a backup.
- The sandbox Khalti page can be slow; if it stalls, show the retry button on the
  order and explain the `expire_unpaid_orders` command that releases stock.
