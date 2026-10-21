"""Local development settings."""
from .base import *  # noqa: F401,F403

# Emails are printed to the console in development instead of being sent.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
