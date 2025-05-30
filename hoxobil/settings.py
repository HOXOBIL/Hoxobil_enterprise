"""
Django settings for hoxobil project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
# This line should have no leading spaces
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path) # This line should also have no leading spaces

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local_dev_fallback_!change_this_for_prod_and_generate_a_real_one!')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

if not DEBUG and (not SECRET_KEY or SECRET_KEY == 'local_dev_fallback_!change_this_for_prod_and_generate_a_real_one!'):
    print("🔴 CRITICAL WARNING: Using a default/weak SECRET_KEY in a non-DEBUG environment. THIS IS INSECURE!")

ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]

# For local development with ngrok if needed
NGROK_HOSTNAME = os.getenv('NGROK_HOSTNAME')
if DEBUG and NGROK_HOSTNAME and NGROK_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(NGROK_HOSTNAME)

if not DEBUG and (not ALLOWED_HOSTS or all(host in ['127.0.0.1', 'localhost'] for host in ALLOWED_HOSTS)):
    print("🔴 CRITICAL WARNING: ALLOWED_HOSTS is not securely configured for production (DEBUG=False). It must list your domain(s).")

CSRF_TRUSTED_ORIGINS_STRING = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STRING.split(',') if origin.strip()]

# For Render deployment if RENDER_EXTERNAL_HOSTNAME is set
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and f"https://{RENDER_EXTERNAL_HOSTNAME}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# For local ngrok if DEBUG is True
if DEBUG and NGROK_HOSTNAME and f"https://{NGROK_HOSTNAME}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{NGROK_HOSTNAME}")

# Fallback for CSRF_TRUSTED_ORIGINS in production if not explicitly set
if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    if ALLOWED_HOSTS:
        for host in ALLOWED_HOSTS:
            # Ensure we don't add localhosts or wildcards, and only add valid domains
            if host not in ['127.0.0.1', 'localhost', '*'] and f"https://{host}" not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
    if not CSRF_TRUSTED_ORIGINS:
        print("🔴 WARNING: CSRF_TRUSTED_ORIGINS is not set for production. POST requests from your domain might fail.")


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',  # For serving static files with runserver when DEBUG=False
    'django.contrib.staticfiles',
    'shop.apps.ShopConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # WhiteNoise for serving static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'shop.middleware.PreLaunchRestrictionMiddleware', # Your custom middleware
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hoxobil.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'hoxobil' / 'templates'], # Global templates directory
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

WSGI_APPLICATION = 'hoxobil.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# This configuration will use DATABASE_URL from .env if set,
# otherwise it defaults to SQLite.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}",
        conn_max_age=600, # Optional for SQLite, but doesn't hurt
        conn_health_checks=True, # Optional for SQLite, but doesn't hurt
        # Ensure NO 'ssl_require=True' here for SQLite default
    )
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_USER_MODEL = 'shop.CustomUser' # Your custom user model

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos' # Your specified time zone
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_production') # For collectstatic in production
STATICFILES_DIRS = [
    BASE_DIR / "static", # Project-wide static files directory
]
# For serving static files efficiently in production with WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Media files (User-uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login and Logout URLs
LOGIN_URL = 'login' # Name of your login URL pattern
LOGIN_REDIRECT_URL = 'home' # Name of URL pattern to redirect to after login
LOGOUT_REDIRECT_URL = 'home' # Name of URL pattern to redirect to after logout


# Email Configuration (reads from .env file)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587)) # Default to 587 if not set
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true' # Explicitly handle SSL
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

    default_email_domain = "yourdomain.com" # Fallback domain
    if ALLOWED_HOSTS and ALLOWED_HOSTS[0] not in ['127.0.0.1', 'localhost', '*']:
        default_email_domain = ALLOWED_HOSTS[0]
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'HOXOBIL <noreply@{default_email_domain}>')
    SERVER_EMAIL = DEFAULT_FROM_EMAIL # For server error notifications

# API Keys (reads from .env file)
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PRINTIFY_API_TOKEN = os.getenv('PRINTIFY_API_TOKEN')
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID')


# Production Security Settings (activated when DEBUG=False)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # For deployments behind a reverse proxy like Nginx or Heroku/Render
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Only redirect to SSL if the environment variable is explicitly set to True
    SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'true'

    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 0)) # Default to 0 (off)
    if SECURE_HSTS_SECONDS > 0:
        SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
        SECURE_HSTS_PRELOAD = os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'False').lower() == 'true'

    X_FRAME_OPTIONS = 'DENY' # Good default for clickjacking protection
    SECURE_CONTENT_TYPE_NOSNIFF = True
