"""Production settings.

Hardening (HTTPS, HSTS, secure cookies) is added in the deployment phase.
This phase only sets what the skeleton needs to serve correctly.
"""
from .base import *  # noqa: F401,F403

# Send real email over SMTP in production, using credentials from .env.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# WhiteNoise serves static files in production (dev uses Django's own server).
# It sits directly after the security middleware.
MIDDLEWARE = [
    MIDDLEWARE[0],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]

# WhiteNoise compresses static files and adds content hashes for caching.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
