"""Review submission (one view): a logged-in, eligible customer posts a review.

The form lives on the product page, so this view only handles the POST and then
redirects back to the product with a message.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from catalog.models import Product

from . import services
from .forms import ReviewForm


@require_POST
@login_required
def add_review(request, slug):
    """Save a review if the customer is eligible, then return to the product."""
    product = get_object_or_404(Product, slug=slug, is_active=True)

    if not services.can_review(request.user, product):
        messages.error(
            request,
            "You can review a mattress only after an order of it is delivered, "
            "and only once.",
        )
        return redirect(product.get_absolute_url())

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.product = product
        review.save()
        messages.success(request, "Thank you for your review.")
    else:
        messages.error(request, "Please check your review and try again.")
    return redirect(product.get_absolute_url())
