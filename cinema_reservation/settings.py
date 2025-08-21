from pathlib import Path
import os
import secrets

# -------------------------------
# Project Base Directory
# -------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------
# Security & Secrets
# -------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-u0(-j67*szm(@!gfg&!l4m422ui)h71_9l-7gk^@$&1n=27h9o'
)

DEBUG = True

ALLOWED_HOSTS = []

# Signed URL secret (keep in env for production)
SIGNED_URL_SECRET = os.environ.get(
    'SIGNED_URL_SECRET',
    'b8c3af5f9e0f44f4bda3d298f5c0f3d7f83f2e9f4b6d4a0a9b17f3cd8c8f7a23'
)

# -------------------------------
# Chapa Payment
# -------------------------------
CHAPA_SECRET_KEY = os.environ.get(
    'CHAPA_SECRET_KEY',
    'CHASECK_TEST-LVVM7kiTEAfpgTT9ULzRH4qm4dtac79i'
)
CHAPA_BASE_URL = 'https://api.chapa.co/v1/transaction/initialize'
CHAPA_VERIFY_URL = 'https://api.chapa.co/v1/transaction/verify/'

# -------------------------------
# Applications
# -------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'reservations',
    'streaming',
    'translations'
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # i18n
    'translations.middleware.JSONTranslationMiddleware',  # your JSON translation middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'cinema_reservation.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'translations.context_processors.translation',        
                    ],
        },
    },
]

LOGIN_URL = '/streaming/login/'

WSGI_APPLICATION = 'cinema_reservation.wsgi.application'

# -------------------------------
# Database
# -------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# -------------------------------
# Password Validators
# -------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# -------------------------------
# Internationalization
# -------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('am', 'Amharic'),
    ('ti', 'Tigrigna'),
    ('om', 'Oromiffa'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# -------------------------------
# Static and Media
# -------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# -------------------------------
# Default Primary Key
# -------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------
# Email Configuration
# -------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = 'hagereselam25@gmail.com'
EMAIL_HOST_PASSWORD = 'zdcurgoccldphprg'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
