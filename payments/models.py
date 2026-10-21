"""Payment model.

One Payment row records an attempt to pay for an order through Khalti. The row
is created when we start a payment (status Initiated) and updated after we ask
Khalti what happened (status Completed or Failed). An order is only ever marked
Paid from a verified Khalti lookup, never from the browser.
"""
from django.db import models


class PaymentStatus(models.TextChoices):
    INITIATED = "initiated", "Initiated"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Payment(models.Model):
    """A single online payment attempt for an order."""

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="payments"
    )
    provider = models.CharField(max_length=20, default="khalti")
    # Khalti's identifier for the attempt, returned by initiate and used at lookup.
    pidx = models.CharField(max_length=64, blank=True)
    # Amount in paisa (Khalti works in paisa), stored as sent to Khalti.
    amount = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED
    )
    # The raw lookup response from Khalti, kept for troubleshooting.
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} {self.status} for {self.order}"
