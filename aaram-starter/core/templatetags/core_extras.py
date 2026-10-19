"""Template filters for the store."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


def _group_nepali(digits):
    """Group an integer string the Nepali way: last 3, then pairs.

    1000 -> "1,000"; 125000 -> "1,25,000"; 1250000 -> "12,50,000".
    """
    if len(digits) <= 3:
        return digits
    last_three = digits[-3:]
    rest = digits[:-3]
    pairs = []
    while len(rest) > 2:
        pairs.insert(0, rest[-2:])
        rest = rest[:-2]
    pairs.insert(0, rest)
    return ",".join(pairs) + "," + last_three


@register.filter
def npr(value):
    """Format a rupee amount with Nepali grouping, e.g. "Rs. 1,25,000".

    Prices are whole rupees, so paise are shown only when present.
    """
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return ""
    rupees = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    text = _group_nepali(str(abs(rupees)))
    sign = "-" if rupees < 0 else ""
    return f"Rs. {sign}{text}"
