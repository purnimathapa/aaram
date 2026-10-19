"""Business rules for the accounts app."""
from django.db import transaction

from .models import Address


@transaction.atomic
def save_address(address):
    """Save an address, keeping at most one default per user.

    When this address is the default, clear the user's other defaults first so
    the one-default-per-user database constraint is never violated.
    """
    if address.is_default:
        Address.objects.filter(
            user=address.user, is_default=True
        ).exclude(pk=address.pk).update(is_default=False)
    address.save()
