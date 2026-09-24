"""See ``.env.example`` for every variable read here."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# api/
BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")


def env(name, default=None, *, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_bool(name, default=False):
    return str(os.environ.get(name, default)).lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    # Local
    "common",
    "users",
    "courses",
    "enrollments",
    "commerce",
    "reviews",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_USER_MODEL = "users.User"

# Only superusers have Django passwords (for /admin/); Clerk owns the rest.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "users.authentication.ClerkAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

CLERK_SECRET_KEY = env("CLERK_SECRET_KEY", "")
CLERK_JWKS_URL = env("CLERK_JWKS_URL", "")
CLERK_ISSUER = env("CLERK_ISSUER", "")
CLERK_AUTHORIZED_PARTIES = env_list("CLERK_AUTHORIZED_PARTIES")
CLERK_JWKS_CACHE_SECONDS = int(env("CLERK_JWKS_CACHE_SECONDS", "3600"))
CLERK_WEBHOOK_SIGNING_SECRET = env("CLERK_WEBHOOK_SIGNING_SECRET", "")

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:3000")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", "")
AWS_PRIVATE_BUCKET_NAME = env("AWS_PRIVATE_BUCKET_NAME", "")
AWS_THUMBNAIL_BUCKET_NAME = env("AWS_THUMBNAIL_BUCKET_NAME", "")
CLOUDFRONT_DOMAIN = env("CLOUDFRONT_DOMAIN", "")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}
