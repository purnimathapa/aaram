"""Forms for registration, profile and the address book."""
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Address, User
from .validators import validate_nepali_mobile


class RegisterForm(UserCreationForm):
    """Sign-up form that collects name, email, phone and a password."""

    phone = forms.CharField(max_length=20, validators=[validate_nepali_mobile])

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]


class ProfileForm(forms.ModelForm):
    """Edit the signed-in user's name and phone. Email is not editable here."""

    phone = forms.CharField(
        max_length=20, required=False, validators=[validate_nepali_mobile]
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]


class AddressForm(forms.ModelForm):
    """Add or edit a delivery address."""

    class Meta:
        model = Address
        fields = [
            "recipient",
            "phone",
            "province",
            "district",
            "municipality",
            "ward_no",
            "street_tole",
            "landmark",
            "is_default",
        ]
