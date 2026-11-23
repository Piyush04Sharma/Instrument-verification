"""
Settings for the Online Verification System for Weighing and Measuring Instruments.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# For a real deployment, change the key, set DEBUG = False and fill ALLOWED_HOSTS.
SECRET_KEY = "django-insecure-change-me-before-deploying-this-project"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # project apps
    "accounts",
    "instruments",
    "verification",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",  # CSRF protection for every POST form
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "verification_system.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "verification.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "verification_system.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# All data (users, instruments, applications, payments, certificates...) is
# stored in this database through the Django ORM.
# SQLite needs no setup; the file db.sqlite3 is created by "migrate".
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# To use MySQL instead (pip install mysqlclient), replace the block above with:
#
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.mysql",
#         "NAME": "verification_db",
#         "USER": "root",
#         "PASSWORD": "your-password",
#         "HOST": "127.0.0.1",
#         "PORT": "3306",
#     }
# }
#
# To use PostgreSQL (pip install psycopg2-binary), use
# "django.db.backends.postgresql" with the same keys.

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Uploaded documents. They are NOT served directly by URL; the
# "document_download" view checks who is asking first.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "home"

# Sessions (stored in the database): two weeks
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14

# Notification emails are printed in the terminal while developing.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@verification.local"
