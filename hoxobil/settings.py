"""
Django settings for hoxobil project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url 

# BASE_DIR should be defined before it's used by load_dotenv if .env is at project root
BASE_DIR = Path(__file__).resolve().parent.parent 
env_path = BASE_DIR / '.env' # Assumes .env is in the same directory as manage.py
load_dotenv(dotenv_path=env_path)


# SECURITY WARNING: keep the secret key used in production secret!
# Ensure DJANGO_SECRET_KEY is set in your .env file for production
# For local development, a default is provided if the env var is not set.
# Using a very distinct fallback string to make it easy to identify if it's being used.
DEFAULT_FALLBACK_SECRET_KEY = 'local_dev_fallback_!this_is_not_secure_for_production_generate_a_real_one!'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', DEFAULT_FALLBACK_SECRET_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG=False in your .env file (or server environment) for production.
# Defaults to True for local development if not set.
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

if not DEBUG and (not SECRET_KEY or SECRET_KEY == DEFAULT_FALLBACK_SECRET_KEY):
    print("🔴 CRITICAL WARNING: Using a default/weak SECRET_KEY in a non-DEBUG environment. THIS IS INSECURE!")
    # For a real production environment, consider raising an ImproperlyConfigured error:
    # from django.core.exceptions import ImproperlyConfigured
    # if os.getenv('DJANGO_ENV') == 'production': # Example: check for a production environment flag
    #     raise ImproperlyConfigured("CRITICAL: A strong, unique DJANGO_SECRET_KEY must be set in the production environment.")


ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]
NGROK_HOSTNAME = os.getenv('NGROK_HOSTNAME') # For local testing with ngrok
if DEBUG and NGROK_HOSTNAME and NGROK_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(NGROK_HOSTNAME)

# Safety check for ALLOWED_HOSTS in production
if not DEBUG and (not ALLOWED_HOSTS or all(host in ['127.0.0.1', 'localhost'] for host in ALLOWED_HOSTS)):
     print("🔴 CRITICAL WARNING: ALLOWED_HOSTS is not securely configured for production (DEBUG=False). It must list your domain(s).")
    # if os.getenv('DJANGO_ENV') == 'production':
    #     from django.core.exceptions import ImproperlyConfigured
    #     raise ImproperlyConfigured("ALLOWED_HOSTS must be set to your domain(s) in production via the DJANGO_ALLOWED_HOSTS environment variable.")


CSRF_TRUSTED_ORIGINS_STRING = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STRING.split(',') if origin.strip()]
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME') # For Render deployment
if RENDER_EXTERNAL_HOSTNAME and f"https://{RENDER_EXTERNAL_HOSTNAME}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
if DEBUG and NGROK_HOSTNAME and f"https://{NGROK_HOSTNAME}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{NGROK_HOSTNAME}")
if not DEBUG and not CSRF_TRUSTED_ORIGINS: # If DEBUG is False and list is empty
    # Try to infer from ALLOWED_HOSTS if not explicitly set, but explicit is better
    if ALLOWED_HOSTS:
        for host in ALLOWED_HOSTS:
            if host not in ['127.0.0.1', 'localhost', '*'] and f"https://{host}" not in CSRF_TRUSTED_ORIGINS:
                 CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
    if not CSRF_TRUSTED_ORIGINS: # If still empty
        print("🔴 WARNING: CSRF_TRUSTED_ORIGINS is not set for production. POST requests from your domain might fail.")


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',      # Django's authentication framework
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # For serving static files with Whitenoise in development
    'django.contrib.staticfiles',
    'shop.apps.ShopConfig', # Explicitly point to your app's config
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'shop.middleware.PreLaunchRestrictionMiddleware', # Your custom middleware
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hoxobil.urls' # Your project's main urls.py

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

WSGI_APPLICATION = 'hoxobil.wsgi.application' # Your project's wsgi.py


# Database
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}",
        conn_max_age=600, 
        conn_health_checks=True,
    )
}

# Custom User Model
AUTH_USER_MODEL = 'shop.CustomUser' # Tells Django to use your CustomUser model in the 'shop' app

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos' 
USE_I18N = True
USE_TZ = True 

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_production') 
# To resolve the warning: Create an empty 'static' folder in your project root (hoxobil/static/)
# OR comment out/remove the STATICFILES_DIRS line if you only use app-specific static folders.
STATICFILES_DIRS = [
    BASE_DIR / "static", 
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User-uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles') 

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'login' # Name of your login URL pattern
LOGIN_REDIRECT_URL = 'home' # Name of URL pattern to redirect to after successful login
LOGOUT_REDIRECT_URL = 'home' # Name of URL pattern to redirect to after logout

# Email Backend 
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587)) 
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    # Ensure ALLOWED_HOSTS is not empty before trying to access ALLOWED_HOSTS[0]
    # and that it's a real domain for constructing DEFAULT_FROM_EMAIL
    default_email_domain = "yourdomain.com" # Provide a sensible default domain
    if ALLOWED_HOSTS and ALLOWED_HOSTS[0] not in ['127.0.0.1', 'localhost', '*']:
        default_email_domain = ALLOWED_HOSTS[0]
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'HOXOBIL <noreply@{default_email_domain}>')
    SERVER_EMAIL = DEFAULT_FROM_EMAIL 

# API Keys
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PRINTIFY_API_TOKEN = os.getenv('PRINTIFY_API_TOKEN')
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID')

# Production Security Settings
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 0)) # Default to 0 (off)
    if SECURE_HSTS_SECONDS > 0: 
        SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
        SECURE_HSTS_PRELOAD = os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'False').lower() == 'true'
    # SECURE_BROWSER_XSS_FILTER = True # Obsolete in modern browsers, can be removed
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
