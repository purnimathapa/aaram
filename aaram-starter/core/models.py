"""Core models.

Province holds the per-province delivery charge and estimated delivery time
used at checkout. StoreSettings is added in a later phase.
"""
from django.db import models


class Province(models.Model):
    """One of Nepal's seven provinces, with its delivery charge and ETA."""

    name = models.CharField(max_length=50, unique=True)
    # Money is always stored as a decimal, never a float. Charge is in NPR.
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2)
    est_days_min = models.PositiveSmallIntegerField()
    est_days_max = models.PositiveSmallIntegerField()
    # Lets staff turn off provinces AARAM cannot deliver to yet.
    is_serviceable = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(delivery_charge__gte=0),
                name="province_delivery_charge_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(est_days_min__lte=models.F("est_days_max")),
                name="province_est_days_min_not_after_max",
            ),
        ]

    def __str__(self):
        return self.name
