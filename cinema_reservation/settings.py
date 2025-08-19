from pathlib import Path
import os
import secrets

# Generate once, then keep it the same (don’t regenerate every restart)
SIGNED_URL_SECRET = "b8c3af5f9e0f44f4bda3d298f5c0f3d7f83f2e9f4b6d4a0a9b17f3cd8c8f7a23"
# You can generate your own with:
# secrets.token_hex(32)


CHAPA_SECRET_KEY = 'CHASECK_TEST-LVVM7kiTEAfpgTT9ULzRH4qm4dtac79i'
CHAPA_BASE_URL = 'https://api.chapa.co/v1/transaction/initialize'
CHAPA_VERIFY_URL = 'https://api.chapa.co/v1/transaction/verify/'


# Define BASE_DIR before using it
BASE_DIR = Path(__file__).resolve().parent.parent

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Static files
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-u0(-j67*szm(@!gfg&!l4m422ui)h71_9l-7gk^@$&1n=27h9o'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'reservations',
    'streaming',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'cinema_reservation.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en'  # Default language

LANGUAGES = [
    ('en', 'English'),
    ('am', 'Amharic'),
    ('ti', 'Tigrigna'),
    ('om', 'Oromiffa'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

USE_I18N = True
USE_L10N = True
USE_TZ = True

SIGNED_URL_SECRET = os.environ.get('SIGNED_URL_SECRET', 'change-this-in-prod')

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# -------------------------------
# ✅ Email Configuration (Gmail)
# -------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = 'hagereselam25@gmail.com'         
EMAIL_HOST_PASSWORD = 'zdcurgoccldphprg'  
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]
