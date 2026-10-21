"""Cancel Khalti orders that were never paid.

A customer who starts a Khalti payment but does not finish leaves an order that
is Pending and Unpaid, holding stock. This command, run on a schedule (for
example by cron), cancels such orders once they are older than 30 minutes so
the stock is released. Cash-on-delivery orders are never touched.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from orders import services
from orders.models import Order, OrderStatus, PaymentMethod, PaymentStatus


class Command(BaseCommand):
    help = "Cancel unpaid Khalti orders older than 30 minutes and restore stock."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=30)
        stale = Order.objects.filter(
            payment_method=PaymentMethod.KHALTI,
            payment_status=PaymentStatus.UNPAID,
            status=OrderStatus.PENDING,
            placed_at__lt=cutoff,
        )

        cancelled = 0
        for order in stale:
            # change_status restores the stock and records the change.
            services.change_status(
                order,
                OrderStatus.CANCELLED,
                actor=None,
                note="Cancelled automatically: Khalti payment not completed in time.",
            )
            cancelled += 1

        self.stdout.write(f"Cancelled {cancelled} unpaid Khalti order(s).")
