"""Views for registration, profile and the address book.

Authentication, password reset and password change use Django's built-in
views, wired up in urls.py. The views here cover sign-up, the profile page and
the customer's own addresses. Address views always filter by request.user, so
one customer can never see or change another customer's address.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.emails import send_welcome_email

from .forms import AddressForm, ProfileForm, RegisterForm
from .models import Address
from .services import save_address


def register(request):
    """Create a new account and sign the person in."""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_welcome_email(user)
            login(request, user)
            messages.success(request, "Welcome to AARAM. Your account is ready.")
            return redirect("accounts:profile")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    """Show and edit the signed-in user's name and phone."""
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def address_list(request):
    """List only the signed-in user's addresses."""
    addresses = request.user.addresses.all()
    return render(request, "accounts/address_list.html", {"addresses": addresses})


@login_required
def address_add(request):
    """Add a new address for the signed-in user."""
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            save_address(address)
            messages.success(request, "Address added.")
            return redirect("accounts:address_list")
    else:
        form = AddressForm()
    return render(
        request, "accounts/address_form.html", {"form": form, "title": "Add address"}
    )


@login_required
def address_edit(request, pk):
    """Edit one of the signed-in user's addresses; another user's 404s."""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            save_address(form.save(commit=False))
            messages.success(request, "Address updated.")
            return redirect("accounts:address_list")
    else:
        form = AddressForm(instance=address)
    return render(
        request, "accounts/address_form.html", {"form": form, "title": "Edit address"}
    )


@login_required
def address_delete(request, pk):
    """Delete one of the signed-in user's addresses (POST only)."""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        address.delete()
        messages.success(request, "Address removed.")
        return redirect("accounts:address_list")
    return render(
        request, "accounts/address_confirm_delete.html", {"address": address}
    )
