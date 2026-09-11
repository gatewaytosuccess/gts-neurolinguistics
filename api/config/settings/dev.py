"""Local development settings."""

from .base import *  # noqa: F403
from .base import env_list

DEBUG = True

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")

# Browsable API is a useful thing to have while the frontend is being built.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
