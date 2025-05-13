"""
Django settings for hoxobil project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url 

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local_dev_fallback_secret_key_!change_this_if_no_env!')
if not SECRET_KEY or SECRET_KEY == 'your-default-strong-secret-key-for-local-dev-if-env-not-set':
    print("🔴 WARNING: Using a default/weak SECRET_KEY. Set a strong DJANGO_SECRET_KEY in .env for production!")
    if os.getenv('DJANGO_ENV') == 'production': # Add DJANGO_ENV=production to your production environment
         raise ValueError("CRITICAL: DJANGO_SECRET_KEY must be set in production environment!")


DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]
NGROK_HOSTNAME = os.getenv('NGROK_HOSTNAME')
if DEBUG and NGROK_HOSTNAME and NGROK_HOSTNAME not in ALLOWED_HOSTS: # Add ngrok only if in DEBUG and not already present
    ALLOWED_HOSTS.append(NGROK_HOSTNAME)

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
    BASE_DIR / "static",  # This resolves to /home/HOXOBIL/hoxobil/static
]

# Ensure the directory C:\Users\yanex\OneDrive\Desktop\hoxobil\static exists if you use STATICFILES_DIRS.
# If not, create it or comment out STATICFILES_DIRS.

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
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'webmaster@{ALLOWED_HOSTS[0] if ALLOWED_HOSTS else "localhost"}')
    SERVER_EMAIL = DEFAULT_FROM_EMAIL 

PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PRINTIFY_API_TOKEN = os.getenv('PRINTIFY_API_TOKEN')
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID')

# --- Production Security Settings ---
# These should only be active when DEBUG is False (i.e., in production)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True # Ensure your hosting handles SSL termination correctly if True
    
    # HSTS Settings (use with caution, understand implications before enabling fully)
    # Start with a small value for SECURE_HSTS_SECONDS for testing, e.g., 3600 (1 hour)
    # before committing to a long duration.
   # In settings.py, inside if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 3600)) # Default to 1 hour for initial testing
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
    SECURE_HSTS_PRELOAD = os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'False').lower() == 'true'
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # Ensure ALLOWED_HOSTS is properly set for production in your .env or server environment
    if not ALLOWED_HOSTS_STRING or '127.0.0.1' in ALLOWED_HOSTS or 'localhost' in ALLOWED_HOSTS:
        print("🔴 CRITICAL WARNING: ALLOWED_HOSTS is not securely configured for production!")
        # Consider raising an ImproperlyConfigured error if in a production environment
        # if os.getenv('DJANGO_ENV') == 'production':
        #     raise ImproperlyConfigured("ALLOWED_HOSTS must be set to your domain(s) in production.")

# Ensure SECRET_KEY is not the default fallback in production
if not DEBUG and SECRET_KEY == 'your-default-strong-secret-key-for-local-dev-if-env-not-set':
    print("🔴 CRITICAL WARNING: Using a default fallback SECRET_KEY in a non-DEBUG environment. THIS IS INSECURE!")
    # if os.getenv('DJANGO_ENV') == 'production':
    #     raise ImproperlyConfigured("A strong, unique DJANGO_SECRET_KEY must be set in production.")

