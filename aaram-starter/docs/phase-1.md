# Phase 1: Accounts

## What this phase built

Everything a customer needs to have an account and save where their mattress
should go: registration, email login and logout, password reset by email and
password change, a profile page, and an address book of Nepali delivery
addresses. It also adds the seven provinces (with their delivery charge and
estimated delivery time) that checkout will use later.

## New and changed files

### Models and data
- `core/models.py` - adds `Province` (name, `delivery_charge`, `est_days_min`, `est_days_max`, `is_serviceable`). Database check constraints keep the charge at or above zero and `est_days_min` no greater than `est_days_max`.
- `core/admin.py` - registers `Province` so staff can edit charges and serviceability.
- `core/migrations/0001_initial.py` - creates the province table.
- `fixtures/provinces.json` - the seven provinces with clearly sample charges and ETAs (Bagmati cheapest and fastest, Karnali and Sudurpashchim the most). Load with `python manage.py loaddata fixtures/provinces.json`.
- `accounts/models.py` - adds `Address` (user, province, recipient, phone, district, municipality, ward_no, street_tole, landmark, is_default). A check constraint keeps `ward_no` at least 1; a **partial unique constraint** allows at most one default address per user.
- `accounts/migrations/0002_address.py` - creates the address table.
- `accounts/validators.py` - `validate_nepali_mobile`, a regex validator for ten-digit numbers starting 96, 97 or 98.

### Forms, services, views, URLs
- `accounts/forms.py` - `RegisterForm` (name, email, phone, password twice), `ProfileForm` (name and phone; email is read-only), `AddressForm`.
- `accounts/services.py` - `save_address`, which saves an address and, when it is the default, clears the user's other defaults first so the one-default constraint is never violated.
- `accounts/views.py` - `register`, `profile`, and the four address views. Every address view looks the address up with `user=request.user`, so another customer's address returns 404.
- `accounts/urls.py` - sign-up, login, logout (POST only), password reset (four views), password change (two views), profile and the address book, under the `accounts` namespace. Authentication and password views reuse Django's built-in views; we supply templates and success URLs.
- `config/urls.py` - includes `accounts.urls` at `/accounts/`.
- `config/settings/base.py` - `LOGIN_URL`, `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL`.
- `accounts/admin.py` - registers `Address`.

### Templates and styles
- `templates/partials/form_fields.html` - reusable rendering of a form: label above each field, help text, and plain error messages in red under the field.
- `templates/accounts/` - `register.html`, `profile.html`, `address_list.html`, `address_form.html`, `address_confirm_delete.html`.
- `templates/registration/` - `login.html`, the four password-reset pages, the reset email body, and the two password-change pages.
- `templates/partials/header.html` - the account icon now links to the profile page.
- `static/css/main.css` - new form, account, auth and address-book sections.

### Tests
- `accounts/tests.py` - eleven checks (see below).

## How to test it manually

1. `python manage.py migrate` then `python manage.py loaddata fixtures/provinces.json`.
2. `python manage.py runserver`, open http://127.0.0.1:8000/accounts/register/ and create an account. You land on your profile, logged in.
3. Open **My addresses**, add an address, and mark it default. Add a second default and confirm the first is no longer the default.
4. Edit and remove an address. Try opening another user's address by changing the number in the URL - you get a 404.
5. Log out from the profile page, then log in again with your email and password.
6. Use **Forgot your password?**. The reset email is printed in the terminal running `runserver`; open the link in it and set a new password.
7. Visit http://127.0.0.1:8000/admin/ and confirm Provinces and Addresses appear.

## Likely defense questions

1. **How do you stop one customer from seeing another's address?**
   Every address view fetches the record with `get_object_or_404(Address, pk=pk, user=request.user)`, and the list view uses `request.user.addresses`. If the address is not the signed-in user's, the lookup fails and Django returns 404, so the URL cannot be guessed to reach someone else's data.

2. **How is "one default address per user" enforced?**
   By a partial unique constraint in the database: `UniqueConstraint(fields=["user"], condition=Q(is_default=True))`. Even if the application logic had a bug, the database would reject a second default. The `save_address` service clears the previous default inside one transaction before saving the new one, so the normal flow never hits that error.

3. **Why validate the phone number with a regex, and where does it run?**
   Nepali mobile numbers are ten digits starting 96, 97 or 98. `validate_nepali_mobile` is attached to the `Address.phone` field and to the phone fields on the register and profile forms, so bad numbers are caught both in forms and at the model level.

4. **Why use Django's built-in auth and password-reset views instead of writing our own?**
   They are well tested and handle security details correctly - password hashing, one-time signed reset tokens, and not revealing whether an email is registered. We only provide templates and the success URLs, which keeps our code small and safe to defend.

5. **Why is email read-only on the profile page?**
   Email is the login identifier and must stay unique. Editing name and phone is low risk; changing the login email brings extra edge cases (uniqueness, staying logged in), so this phase keeps email fixed and leaves changing it out of scope.

## Tests in this phase

- Profile and address pages redirect anonymous users to the login page (login required).
- Another user's address edit and delete both return 404, and the address is not deleted.
- Adding a second default address unsets the first; the database rejects two defaults directly.
- The Nepali phone validator rejects a bad number and accepts a valid one.
- The province check constraint rejects `est_days_min` greater than `est_days_max`.
- Registration creates the user and logs them in.
