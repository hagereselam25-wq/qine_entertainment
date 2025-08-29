import os
from pathlib import Path
import environ

# ======================
# Base directory
# ======================
BASE_DIR = Path(__file__).resolve().parent.parent

# ======================
# Environment variables
# ======================
env = environ.Env(
    DEBUG=(bool, False)  # Default DEBUG = False
)

# Read from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ======================
# Security
# ======================
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# ======================
# Applications
# ======================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Your apps
    "reservations",
    "streaming",
]

# ======================
# Middleware
# ======================
MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Added for static files
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cinema_reservation.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "cinema_reservation.wsgi.application"

# ======================
# Database
# ======================
DATABASES = {
    "default": env.db()  # Reads DATABASE_URL
}

# ======================
# Password validation
# ======================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ======================
# Internationalization
# ======================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Addis_Ababa"
USE_I18N = True
USE_TZ = True

# ======================
# Static & Media files
# ======================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise static files storage
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ======================
# Email config
# ======================
EMAIL_BACKEND = env("EMAIL_BACKEND")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

# ======================
# Custom secrets & API keys
# ======================
SIGNED_URL_SECRET = env("SIGNED_URL_SECRET")
CHAPA_SECRET_KEY = env("CHAPA_SECRET_KEY")
CHAPA_BASE_URL = env("CHAPA_BASE_URL")
CHAPA_VERIFY_URL = env("CHAPA_VERIFY_URL")

# ======================
# Default primary key field type
# ======================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redirect users to this login page when @login_required is used
LOGIN_URL = '/streaming/login/'
