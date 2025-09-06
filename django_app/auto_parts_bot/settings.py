"""
Django settings for auto_parts_bot project.
"""

import os
from pathlib import Path

# Try to import optional packages, fallback if not available
try:
    from decouple import config
except ImportError:
    def config(key, default=None, cast=str):
        value = os.environ.get(key, default)
        if cast and value is not None:
            return cast(value)
        return value

try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-g&m_ds(8y5c=8@8*jak&4hr_2c8l8c&2-ms%cinzvj-t(cgy%^')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0,193.187.129.94,dashboard.tashaleeh.com', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
INSTALLED_APPS = [
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    
    # Local apps
    'bot',
    'dashboard',
]
MIDDLEWARE = [
    # 'corsheaders.middleware.CorsMiddleware',  # Only if corsheaders is installed
    'django.middleware.security.SecurityMiddleware',
    # 'whitenoise.middleware.WhiteNoiseMiddleware',  # Only if whitenoise is installed
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'auto_parts_bot.urls'

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

WSGI_APPLICATION = 'auto_parts_bot.wsgi.application'

# Database
DATABASE_URL = config('DATABASE_URL', default='sqlite:///db.sqlite3')

if dj_database_url:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Fallback database configuration
    if DATABASE_URL.startswith('postgresql://'):
        # Parse PostgreSQL URL manually
        import urllib.parse
        url = urllib.parse.urlparse(DATABASE_URL)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': url.path[1:],
                'USER': url.username,
                'PASSWORD': url.password,
                'HOST': url.hostname,
                'PORT': url.port,
            }
        }
    else:
        # Default SQLite
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
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Django Admin Custom CSS
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Custom user model
AUTH_USER_MODEL = 'bot.User'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# CSRF settings - Add trusted origins for Docker/Nginx setup
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8888',
    'http://127.0.0.1:8888',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://193.187.129.94:8888',
    'https://dashboard.tashaleeh.com',
    'http://dashboard.tashaleeh.com',
]

# Telegram Bot settings
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_WEBHOOK_URL = config('TELEGRAM_WEBHOOK_URL', default='http://localhost:8000/bot/webhook/telegram/')

# n8n Integration
N8N_WEBHOOK_URL = config('N8N_WEBHOOK_URL', default='http://n8n:5678')

# Business settings
DEFAULT_COMMISSION_PERCENTAGE = config('DEFAULT_COMMISSION_PERCENTAGE', default=2.0, cast=float)
DEFAULT_PAYMENT_URL = config('DEFAULT_PAYMENT_URL', default='https://your-payment-gateway.com')
REQUEST_EXPIRY_HOURS = config('REQUEST_EXPIRY_HOURS', default=6, cast=int)

# Google Sheets settings (optional)
GOOGLE_SHEETS_API_KEY = config('GOOGLE_SHEETS_API_KEY', default='')
GOOGLE_SHEETS_SPREADSHEET_ID = config('GOOGLE_SHEETS_SPREADSHEET_ID', default='')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'bot': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Admin Interface settings
X_FRAME_OPTIONS = 'SAMEORIGIN'
SILENCED_SYSTEM_CHECKS = ['security.W019']

# Django Admin Interface Theme
ADMIN_INTERFACE_THEME = {
    'name': 'auto_parts_bot_theme',
    'title': 'نظام قطع الغيار - لوحة التحكم',
    'subtitle': 'إدارة البوت والمخازن والطلبات',
    'logo': 'admin/img/logo.png',
    'logo_color': '#2C3E50',
    'color': '#3498DB',
    'recent_actions': True,
    'breadcrumbs': True,
    'show_sidebar': True,
    'navigation_expanded': True,
    'icons': {
        'auth': 'fas fa-users-cog',
        'bot': 'fas fa-robot',
        'dashboard': 'fas fa-chart-line',
    },
}

