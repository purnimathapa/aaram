"""Review model.

A customer may leave one review per mattress, and only after an order of that
mattress has been delivered (the eligibility rule lives in reviews/services.py).
Staff can hide a review by turning off is_visible; hidden reviews are kept but
not shown to shoppers.
"""
from django.conf import settings
from django.db import models


class Review(models.Model):
    """One customer's rating and words about one product."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField()  # 1 to 5
    title = models.CharField(max_length=120)
    body = models.TextField()
    # Staff can hide an inappropriate review without deleting it.
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # One review per customer per product.
            models.UniqueConstraint(
                fields=["user", "product"],
                name="one_review_per_user_per_product",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.rating}/5 by {self.user} on {self.product}"
