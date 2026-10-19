"""Tests for accounts: auth access, address ownership, defaults, validation."""
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from core.models import Province

from .forms import AddressForm
from .models import Address, User


class LoginRequiredTests(TestCase):
    def test_profile_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}"
        )

    def test_address_list_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("accounts:address_list"))
        login_url = reverse("accounts:login")
        self.assertRedirects(
            response, f"{login_url}?next={reverse('accounts:address_list')}"
        )


class AddressOwnershipTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(
            name="Bagmati",
            delivery_charge="200.00",
            est_days_min=1,
            est_days_max=3,
        )
        self.owner = User.objects.create_user("owner@example.com", "pass12345")
        self.other = User.objects.create_user("other@example.com", "pass12345")
        self.address = Address.objects.create(
            user=self.owner,
            province=self.province,
            recipient="Owner",
            phone="9801234567",
            district="Kathmandu",
            municipality="Kathmandu",
            ward_no=5,
            street_tole="Baneshwor",
        )

    def test_other_user_cannot_edit_someone_elses_address(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("accounts:address_edit", args=[self.address.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_delete_someone_elses_address(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("accounts:address_delete", args=[self.address.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Address.objects.filter(pk=self.address.pk).exists())


class DefaultAddressTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(
            name="Bagmati",
            delivery_charge="200.00",
            est_days_min=1,
            est_days_max=3,
        )
        self.user = User.objects.create_user("user@example.com", "pass12345")

    def _post_address(self, recipient, is_default):
        data = {
            "recipient": recipient,
            "phone": "9801234567",
            "province": self.province.pk,
            "district": "Kathmandu",
            "municipality": "Kathmandu",
            "ward_no": 5,
            "street_tole": "Baneshwor",
            "landmark": "",
        }
        if is_default:
            data["is_default"] = "on"
        return self.client.post(reverse("accounts:address_add"), data)

    def test_adding_a_new_default_unsets_the_previous_default(self):
        self.client.force_login(self.user)
        self._post_address("First", is_default=True)
        self._post_address("Second", is_default=True)

        defaults = Address.objects.filter(user=self.user, is_default=True)
        self.assertEqual(defaults.count(), 1)
        self.assertEqual(defaults.first().recipient, "Second")

    def test_database_rejects_two_defaults_for_one_user(self):
        Address.objects.create(
            user=self.user,
            province=self.province,
            recipient="First",
            phone="9801234567",
            district="Kathmandu",
            municipality="Kathmandu",
            ward_no=1,
            street_tole="Tole",
            is_default=True,
        )
        # The partial unique constraint must block a second default.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Address.objects.create(
                    user=self.user,
                    province=self.province,
                    recipient="Second",
                    phone="9801234567",
                    district="Kathmandu",
                    municipality="Kathmandu",
                    ward_no=2,
                    street_tole="Tole",
                    is_default=True,
                )


class AddressFormValidationTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(
            name="Bagmati",
            delivery_charge="200.00",
            est_days_min=1,
            est_days_max=3,
        )

    def _data(self, phone):
        return {
            "recipient": "Someone",
            "phone": phone,
            "province": self.province.pk,
            "district": "Kathmandu",
            "municipality": "Kathmandu",
            "ward_no": 5,
            "street_tole": "Baneshwor",
            "landmark": "",
        }

    def test_invalid_nepali_phone_is_rejected(self):
        form = AddressForm(data=self._data("12345"))
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_valid_nepali_phone_is_accepted(self):
        form = AddressForm(data=self._data("9841234567"))
        self.assertTrue(form.is_valid())


class ProvinceConstraintTests(TestCase):
    def test_est_days_min_cannot_exceed_max(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Province.objects.create(
                    name="Broken",
                    delivery_charge="100.00",
                    est_days_min=9,
                    est_days_max=2,
                )


class RegistrationTests(TestCase):
    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Sita",
                "last_name": "Rai",
                "email": "sita@example.com",
                "phone": "9801234567",
                "password1": "strong-pass-123",
                "password2": "strong-pass-123",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertTrue(User.objects.filter(email="sita@example.com").exists())
        # The session now carries an authenticated user.
        self.assertIn("_auth_user_id", self.client.session)
