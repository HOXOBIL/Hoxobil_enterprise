"""
Django settings for hoxobil project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url 

# Load environment variables from .env file (primarily for local development)
# Ensure .env is in the same directory as manage.py (BASE_DIR)
# BASE_DIR is defined after this block, so construct path carefully or define BASE_DIR earlier
# For simplicity, assuming .env is in the same directory as manage.py, which is BASE_DIR
# Corrected BASE_DIR definition to be before load_dotenv that uses it.
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Ensure DJANGO_SECRET_KEY is set in your .env file for production
# For local development, a default is provided if the env var is not set.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local_dev_fallback_secret_key_!change_this_if_no_env_and_generate_a_real_one!')
# The DEBUG variable is defined later, so this check needs to be after DEBUG is defined, or assume DEBUG=False for this check
# if not DEBUG and (not SECRET_KEY or SECRET_KEY == 'local_dev_fallback_secret_key_!change_this_if_no_env_and_generate_a_real_one!'):
#     print("🔴 CRITICAL WARNING: Using a default/weak SECRET_KEY in a non-DEBUG environment. THIS IS INSECURE!")
    # if os.getenv('DJANGO_ENV') == 'production': 
    #     raise ValueError("CRITICAL: DJANGO_SECRET_KEY must be set in production environment!")


# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG=False in your .env file (or server environment) for production.
# Defaults to True for local development if not set.
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

# Now that DEBUG is defined, we can check the SECRET_KEY for production
if not DEBUG and (not SECRET_KEY or SECRET_KEY == 'local_dev_fallback_secret_key_!change_this_if_no_env_and_generate_a_real_one!'):
    print("🔴 CRITICAL WARNING: Using a default/weak SECRET_KEY in a non-DEBUG environment. THIS IS INSECURE!")
    # For a real production environment, you might want to raise an ImproperlyConfigured error here
    # if os.getenv('DJANGO_ENV') == 'production': 
    #     from django.core.exceptions import ImproperlyConfigured
    #     raise ImproperlyConfigured("CRITICAL: A strong, unique DJANGO_SECRET_KEY must be set in the production environment.")


# ALLOWED_HOSTS should be set in .env for production, e.g., DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
# For local development, it defaults to 127.0.0.1 and localhost.
# If using ngrok, add its hostname to your .env's DJANGO_ALLOWED_HOSTS or directly here for testing.
ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()] # Ensure no empty strings from split

# Add ngrok hostname if in DEBUG mode and the NGROK_HOSTNAME env var is set
NGROK_HOSTNAME = os.getenv('NGROK_HOSTNAME')
if DEBUG and NGROK_HOSTNAME and NGROK_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(NGROK_HOSTNAME)

# Safety check for ALLOWED_HOSTS in production
if not DEBUG and not any(host not in ['127.0.0.1', 'localhost'] for host in ALLOWED_HOSTS):
    # This check is a bit too aggressive as ALLOWED_HOSTS should NOT contain 127.0.0.1 or localhost in production
    # A better check is if it's empty or only contains defaults when not in DEBUG
    pass # The actual check for production should be that it contains your domain(s)

if not DEBUG and (not ALLOWED_HOSTS or all(host in ['127.0.0.1', 'localhost'] for host in ALLOWED_HOSTS)):
     print("🔴 CRITICAL WARNING: ALLOWED_HOSTS is not securely configured for production (DEBUG=False). It must list your domain(s).")
    # if os.getenv('DJANGO_ENV') == 'production':
    #     from django.core.exceptions import ImproperlyConfigured
    #     raise ImproperlyConfigured("ALLOWED_HOSTS must be set to your domain(s) in production via the DJANGO_ALLOWED_HOSTS environment variable.")


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # For serving static files with Whitenoise in development
    'django.contrib.staticfiles',
    'shop', # Your application
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise middleware, place high, after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hoxobil.urls' # Matches your project name

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # If your project-level templates are in 'hoxobil/templates/':
        'DIRS': [BASE_DIR / 'hoxobil' / 'templates'], 
        'APP_DIRS': True, # Allows Django to find templates in app directories like 'shop/templates/'
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

WSGI_APPLICATION = 'hoxobil.wsgi.application' # Matches your project name


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
# Uses DATABASE_URL from .env file if available (e.g., for PostgreSQL in production)
# Otherwise, defaults to SQLite for local development.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}",
        conn_max_age=600, 
        conn_health_checks=True, # Requires Django 3.1+
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos' # Set to your specific timezone
USE_I18N = True
USE_TZ = True # Recommended to keep True for timezone-aware datetimes


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = '/static/'
# Directory where `collectstatic` will gather all static files for production.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_production') 

# Directories Django looks for static files in addition to each app's 'static' directory.
# Ensure this directory exists if you are using it, or remove/comment out if not.
STATICFILES_DIRS = [
    BASE_DIR / "static", # Corrected to use Path object directly
]
# To fix the warning: Create an empty 'static' folder in your project root (hoxobil/static/)
# OR comment out/remove the STATICFILES_DIRS line if you only use app-specific static folders.

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Media files (User-uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles') 


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'login' # Name of the URL pattern for your login page
LOGIN_REDIRECT_URL = 'home' # Name of the URL pattern to redirect to after successful login
LOGOUT_REDIRECT_URL = 'home' # Name of the URL pattern to redirect to after logout

# Email Backend 
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # For production (configure with your actual email provider via .env vars):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587)) # Default SMTP port
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    # Ensure ALLOWED_HOSTS is not empty before trying to access ALLOWED_HOSTS[0]
    default_email_domain = ALLOWED_HOSTS[0] if ALLOWED_HOSTS and ALLOWED_HOSTS[0] not in ['127.0.0.1', 'localhost'] else "yourdomain.com"
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'webmaster@{default_email_domain}')
    SERVER_EMAIL = DEFAULT_FROM_EMAIL 


# API Keys (loaded from .env at the top)
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PRINTIFY_API_TOKEN = os.getenv('PRINTIFY_API_TOKEN')
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID')


# --- Production Security Settings ---
# These should only be active when DEBUG is False (i.e., in production)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # SECURE_SSL_REDIRECT should be True if your site is fully HTTPS.
    # If using a reverse proxy (like Nginx) that handles SSL termination, 
    # ensure it correctly sets X-Forwarded-Proto header.
    SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    
    # HSTS Settings: Use with caution. Start with small values for SECURE_HSTS_SECONDS.
    # These are best set via environment variables in production.
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 0)) # Default to 0 (off)
    if SECURE_HSTS_SECONDS > 0: 
        SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
        SECURE_HSTS_PRELOAD = os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'False').lower() == 'true'
    
    SECURE_BROWSER_XSS_FILTER = True # Obsolete in modern browsers, but doesn't hurt
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
