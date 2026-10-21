"""Store emails: welcome, order placed and order status changed.

Each function builds a plain-text and an HTML version from templates in
core/templates/emails/ and sends it with transaction.on_commit, so an email
goes out only once the database change that triggered it is safely committed
(and never for an action that is rolled back). In development the console
backend prints emails; production uses SMTP settings from .env.

Password-reset emails are handled by Django's built-in password reset views.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string


def _send(subject, template_base, context, to_email):
    """Render the text and HTML templates and send after the commit."""
    text_body = render_to_string(f"emails/{template_base}.txt", context)
    html_body = render_to_string(f"emails/{template_base}.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    # Only send if the surrounding transaction commits (runs now if there is none).
    transaction.on_commit(message.send)


def send_welcome_email(user):
    """Welcome a newly registered customer."""
    _send(
        subject="Welcome to AARAM",
        template_base="welcome",
        context={"user": user},
        to_email=user.email,
    )


def send_order_placed_email(order):
    """Confirm that an order has been received."""
    _send(
        subject=f"We received your order {order.order_number}",
        template_base="order_placed",
        context={"order": order},
        to_email=order.user.email,
    )


def send_order_status_email(order):
    """Tell the customer their order moved to a new status."""
    _send(
        subject=f"Order {order.order_number} is now {order.get_status_display()}",
        template_base="order_status",
        context={"order": order},
        to_email=order.user.email,
    )
