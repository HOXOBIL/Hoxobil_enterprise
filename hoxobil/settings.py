"""
Django settings for hoxobil project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url 

# Load environment variables from .env file (primarily for local development)
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local_dev_fallback_secret_key_!change_this_if_no_env_and_generate_a_real_one!')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

if not DEBUG and (not SECRET_KEY or SECRET_KEY == 'local_dev_fallback_secret_key_!change_this_if_no_env_and_generate_a_real_one!'):
    print("🔴 CRITICAL WARNING: Using a default/weak SECRET_KEY in a non-DEBUG environment. THIS IS INSECURE!")
    # from django.core.exceptions import ImproperlyConfigured
    # if os.getenv('DJANGO_ENV') == 'production': 
    #     raise ImproperlyConfigured("CRITICAL: A strong, unique DJANGO_SECRET_KEY must be set in the production environment.")

ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]
NGROK_HOSTNAME = os.getenv('NGROK_HOSTNAME')
if DEBUG and NGROK_HOSTNAME and NGROK_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(NGROK_HOSTNAME)

if not DEBUG and (not ALLOWED_HOSTS or all(host in ['127.0.0.1', 'localhost'] for host in ALLOWED_HOSTS)):
     print("🔴 CRITICAL WARNING: ALLOWED_HOSTS is not securely configured for production (DEBUG=False). It must list your domain(s).")
    # if os.getenv('DJANGO_ENV') == 'production':
    #     from django.core.exceptions import ImproperlyConfigured
    #     raise ImproperlyConfigured("ALLOWED_HOSTS must be set to your domain(s) in production via the DJANGO_ALLOWED_HOSTS environment variable.")

# +++ CSRF Trusted Origins +++
# For production, set DJANGO_CSRF_TRUSTED_ORIGINS in your environment variables
# e.g., DJANGO_CSRF_TRUSTED_ORIGINS=https://www.hoxobil.com,https://hoxobil.onrender.com
CSRF_TRUSTED_ORIGINS_STRING = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STRING.split(',') if origin.strip()]

# Automatically add the Render URL if in production and not explicitly set
# (This is a convenience; explicitly setting via env var is better for multiple domains)
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and f"https://{RENDER_EXTERNAL_HOSTNAME}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# For local development with ngrok if you test POST requests via ngrok
if DEBUG and NGROK_HOSTNAME and f"https://{NGROK_HOSTNAME}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{NGROK_HOSTNAME}")

# Fallback for local development if nothing is set
if DEBUG and not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000']

if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    print("🔴 WARNING: CSRF_TRUSTED_ORIGINS is not set for production. POST requests from your domain might fail.")
    # if os.getenv('DJANGO_ENV') == 'production':
    #     from django.core.exceptions import ImproperlyConfigured
    #     raise ImproperlyConfigured("CSRF_TRUSTED_ORIGINS must be set in production to your site's HTTPS domain(s).")
# +++ End CSRF Trusted Origins +++


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', 
    'django.contrib.staticfiles',
    'shop', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hoxobil.urls' 

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'hoxobil' / 'templates'], 
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

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}",
        conn_max_age=600, 
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos' 
USE_I18N = True
USE_TZ = True 

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_production') 
STATICFILES_DIRS = [
    BASE_DIR / "static", 
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles') 

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login' 
LOGIN_REDIRECT_URL = 'home' 
LOGOUT_REDIRECT_URL = 'home' 

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587)) 
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    default_email_domain = ALLOWED_HOSTS[0] if ALLOWED_HOSTS and ALLOWED_HOSTS[0] not in ['127.0.0.1', 'localhost'] else "yourdomain.com"
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'webmaster@{default_email_domain}')
    SERVER_EMAIL = DEFAULT_FROM_EMAIL 

PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PRINTIFY_API_TOKEN = os.getenv('PRINTIFY_API_TOKEN')
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID')

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 0)) 
    if SECURE_HSTS_SECONDS > 0: 
        SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
        SECURE_HSTS_PRELOAD = os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'False').lower() == 'true'
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
