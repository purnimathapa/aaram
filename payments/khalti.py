"""A small Khalti ePayment client (sandbox).

Two calls are all we need:
- initiate(): tell Khalti about the order and get back a payment_url to send the
  customer to, plus a pidx (payment index) that identifies the attempt.
- lookup(): ask Khalti the real status of a pidx. We trust only this, never the
  parameters Khalti puts on the return URL.

The base URL and secret key come from settings (which read them from .env), so
no credentials live in the code. Amounts are in paisa.
"""
import requests
from django.conf import settings


class KhaltiError(Exception):
    """Khalti could not be reached or returned an error."""


def _headers():
    return {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"}


def _post(path, payload):
    url = settings.KHALTI_BASE_URL + path
    try:
        response = requests.post(url, json=payload, headers=_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        raise KhaltiError(str(error))


def initiate(return_url, website_url, amount_paisa, order_number, order_name):
    """Start a payment and return Khalti's response ({pidx, payment_url, ...})."""
    return _post("epayment/initiate/", {
        "return_url": return_url,
        "website_url": website_url,
        "amount": amount_paisa,
        "purchase_order_id": order_number,
        "purchase_order_name": order_name,
    })


def lookup(pidx):
    """Ask Khalti the real status of a payment ({status, total_amount, ...})."""
    return _post("epayment/lookup/", {"pidx": pidx})
