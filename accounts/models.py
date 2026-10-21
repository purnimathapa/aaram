"""Account models.

AARAM uses email to log in instead of a username, so we define a custom user
model now, before the first migration, as Django requires. Address stores the
Nepali delivery addresses a customer saves for checkout.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .validators import validate_nepali_mobile


class UserManager(BaseUserManager):
    """Create users with an email address instead of a username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """A customer or staff member who signs in with a unique email address."""

    # Email replaces username as the login field; username is removed.
    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=20, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Address(models.Model):
    """A delivery address a customer can reuse at checkout."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    # Deliveries depend on the province, so keep it even if an address is edited.
    province = models.ForeignKey(
        "core.Province",
        on_delete=models.PROTECT,
        related_name="addresses",
    )
    recipient = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, validators=[validate_nepali_mobile])
    district = models.CharField(max_length=50)
    municipality = models.CharField(max_length=100)
    ward_no = models.PositiveSmallIntegerField()
    street_tole = models.CharField(max_length=150)
    landmark = models.CharField(max_length=150, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "recipient"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ward_no__gte=1),
                name="address_ward_no_at_least_one",
            ),
            # At most one default address per user, enforced by the database.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="one_default_address_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.recipient}, {self.municipality}-{self.ward_no}, {self.district}"
