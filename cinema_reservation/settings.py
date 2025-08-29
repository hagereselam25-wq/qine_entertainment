from pathlib import Path
import os
import secrets
from django.utils.translation import gettext_lazy as _
# locates our project base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# secret hash of our secret key

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-u0(-j67*szm(@!gfg&!l4m422ui)h71_9l-7gk^@$&1n=27h9o'
)

DEBUG = True

ALLOWED_HOSTS = []

# hashed secret key for Signed URL secret 
SIGNED_URL_SECRET = os.environ.get(
    'SIGNED_URL_SECRET',
    'b8c3af5f9e0f44f4bda3d298f5c0f3d7f83f2e9f4b6d4a0a9b17f3cd8c8f7a23'
)

# our chapa payment secret key and endpoints

CHAPA_SECRET_KEY = os.environ.get(
    'CHAPA_SECRET_KEY',
    'CHASECK_TEST-LVVM7kiTEAfpgTT9ULzRH4qm4dtac79i' #our secret key to authorize transactions
)
CHAPA_BASE_URL = 'https://api.chapa.co/v1/transaction/initialize' # endpoint to initiate payment
CHAPA_VERIFY_URL = 'https://api.chapa.co/v1/transaction/verify/'  # also an endpoint to verify using url plus reference number

# applications to run our site

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

# this middleware, inspects and monitors layer processor from users request to djangos or apps response
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', 
    'translations.middleware.JSONTranslationMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'cinema_reservation.urls'


#our templates helps django to render/generate html files dynamically
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
                'streaming.context_processors.user_profile_context',    
                    ],
        },
    },
]

# used for loginrequired function, tells Django where to send users when they try to access a page that requires login but are not authenticated
LOGIN_URL = '/streaming/login/'

WSGI_APPLICATION = 'cinema_reservation.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password Validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('en', _('English')),
    ('am', _('Amharic')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static and Media
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# default primary key for auto id generation
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# our email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = 'hagereselam25@gmail.com'
EMAIL_HOST_PASSWORD = 'zdcurgoccldphprg'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
