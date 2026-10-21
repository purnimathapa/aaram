"""Production settings.

Adds the security hardening Django recommends for a live HTTPS site, on top of
the shared settings. All of these are off in development (plain HTTP) and on
here. `python manage.py check --deploy` passes with these in place.
"""
from .base import *  # noqa: F401,F403

# Redirect all HTTP requests to HTTPS, and trust the proxy's forwarded scheme
# (most hosts terminate TLS at a proxy in front of the app).
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Only send the session and CSRF cookies over HTTPS.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Tell browsers to stick to HTTPS for a year (including subdomains).
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Stop the browser guessing content types, and block framing (clickjacking).
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

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
