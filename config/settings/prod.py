"""Production settings.

Hardening (HTTPS, HSTS, secure cookies) is added in the deployment phase.
This phase only sets what the skeleton needs to serve correctly.
"""
from .base import *  # noqa: F401,F403

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
