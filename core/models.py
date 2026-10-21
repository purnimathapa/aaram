"""Core models.

Province holds the per-province delivery charge and estimated delivery time
used at checkout. StoreSettings is a single row of store-wide settings staff
can edit in the admin.
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


class StoreSettings(models.Model):
    """Store-wide settings kept in a single row and edited in the admin.

    Use StoreSettings.load() to read them; it always returns the one row,
    creating it with the defaults on first use.
    """

    # At or below this many in stock, the store shows "Only N left".
    low_stock_threshold = models.PositiveSmallIntegerField(default=3)
    # The most of one variant a customer may put on a single cart line.
    max_qty_per_line = models.PositiveSmallIntegerField(default=5)

    class Meta:
        verbose_name_plural = "store settings"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_qty_per_line__gte=1),
                name="store_max_qty_per_line_at_least_one",
            ),
        ]

    def __str__(self):
        return "Store settings"

    @classmethod
    def load(cls):
        """Return the single settings row, creating it with defaults if needed."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
