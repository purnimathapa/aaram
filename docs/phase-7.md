# Phase 7: Khalti payment (sandbox)

## What this phase built

Online payment with Khalti, alongside the existing Cash on Delivery. At checkout
the customer can choose Khalti; the order is placed as Unpaid and the customer is
sent to Khalti to pay and then returned to the site. We confirm the payment with
our own server-to-server lookup and mark the order Paid only when Khalti reports
it Completed for the exact amount. A customer can retry an unpaid Khalti order,
and a scheduled command cancels Khalti orders that are never paid so their stock
is released.

## New and changed files

### Payments app
- `payments/models.py` - `Payment`: one online payment attempt for an order
  (provider, `pidx`, amount in paisa, status Initiated/Completed/Failed, the raw
  lookup response, timestamps).
- `payments/khalti.py` - a small client: `initiate()` (start a payment, get a
  `payment_url` and `pidx`) and `lookup()` (ask Khalti the real status). The base
  URL and secret key come from settings (`.env`); amounts are in paisa.
- `payments/services.py`:
  - `start_payment(order, return_url, website_url)` - create a `Payment`, ask
    Khalti to initiate it, return the URL to send the customer to.
  - `verify_payment(pidx)` - look the payment up at Khalti and mark the order
    **Paid only** if the lookup says Completed **and** the amount matches.
- `payments/views.py` - `start` (begin or retry a payment for the customer's own
  order) and `callback` (where Khalti returns; it verifies by lookup, ignoring
  the URL's own status and amount).
- `payments/urls.py` - `/payments/khalti/start/<number>/` and
  `/payments/khalti/callback/`.
- `payments/management/commands/expire_unpaid_orders.py` - cancels unpaid Khalti
  orders older than 30 minutes via `change_status` (which restores stock); run on
  a schedule.
- `payments/admin.py` - read-only admin for inspecting payment attempts.
- `payments/migrations/0001_initial.py`.

### Changed
- `orders/services.py` - `place_order` takes a `payment_method` (COD by default)
  and stores it on the order.
- `orders/views.py` - the `place` view reads the chosen method; a Khalti order is
  sent to `payments:start`, a COD order to the confirmation page as before.
- `orders/templates/orders/checkout.html` - the Khalti option is enabled.
- `orders/templates/orders/order_detail.html` - an unpaid, still-pending Khalti
  order shows a "Pay now with Khalti" button (retry).
- `config/settings/base.py`, `.env.example` - `KHALTI_BASE_URL` and
  `KHALTI_SECRET_KEY`.
- `config/urls.py` - includes the payments URLs.

## How to test it manually

Set `KHALTI_SECRET_KEY` in `.env` to a sandbox test key from the Khalti merchant
dashboard first.

1. Add a mattress to the cart and go to checkout. Choose **Khalti** and place the
   order. You are redirected to Khalti's sandbox page.
2. Complete the test payment. Khalti returns you to the site, the order shows as
   Paid, and a `Payment` row is Completed.
3. Start a Khalti order but cancel at Khalti (or just come back). The order stays
   Unpaid and Pending, and its page shows **Pay now with Khalti** to try again.
4. Run `python manage.py expire_unpaid_orders`. An unpaid Khalti order older than
   30 minutes is cancelled and its stock is restored; recent and COD orders are
   left alone.

## Likely defense questions

1. **Why check the payment with a lookup instead of trusting Khalti's return URL?**
   Anyone can change the query parameters on the return URL, so believing a
   `status=Completed` there would let someone mark an order paid without paying.
   Our `callback` view reads only the `pidx` and then calls Khalti's `lookup`
   server-to-server; the order is marked Paid only if that trusted response says
   Completed for the exact amount. A test sends a forged `status=Completed` URL
   while the lookup returns Pending and checks the order stays Unpaid.

2. **Why is the amount checked as well as the status?**
   To make sure the customer paid the full total, not less. We store the amount
   we charged (in paisa) on the `Payment` and compare it to Khalti's
   `total_amount`; a Completed payment for the wrong amount is not accepted.

3. **Where do the Khalti base URL and secret key come from?**
   From settings that read `.env` (`KHALTI_BASE_URL`, default the sandbox, and
   `KHALTI_SECRET_KEY`). The key is never in the code or Git, and the client
   sends it in the `Authorization: Key ...` header.

4. **What happens if the customer never finishes paying?**
   The order stays Pending and Unpaid and still holds its stock, and the customer
   can retry from the order page. The `expire_unpaid_orders` command, run on a
   schedule, cancels such orders after 30 minutes using `change_status`, which
   restores the stock - the same safe path as any other cancel.

5. **Does paying change the order's status?**
   No. Paying sets the payment status to Paid; the order status (Pending,
   Confirmed, ...) is still moved by staff. This keeps "has the customer paid"
   and "where is the order in fulfilment" as two separate facts.
