"""Validators shared by the accounts forms and models."""
from django.core.validators import RegexValidator

# Nepali mobile numbers are ten digits beginning 96, 97 or 98.
validate_nepali_mobile = RegexValidator(
    regex=r"^9[678]\d{8}$",
    message="Enter a valid Nepali mobile number, for example 9801234567.",
)
