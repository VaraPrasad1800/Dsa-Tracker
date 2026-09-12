import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dsa-tracker-local-dev-secret-key-replace-in-prod')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    # Local apps
    'tracker',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'core.wsgi.application'

# Database configuration: PostgreSQL with SQLite fallback
if os.environ.get('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'dsa_tracker'),
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Cache Configuration: Redis with LocMemCache fallback
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 6 * 3600,  # 6 hours TTL per specification
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'dsa-tracker-local-cache',
            'TIMEOUT': 6 * 3600,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tracker.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))
JWT_REFRESH_EXPIRATION_HOURS = int(os.environ.get('JWT_REFRESH_EXPIRATION_HOURS', '168'))  # 7 days

# Email configuration (SendGrid in production, console fallback for dev/test)
# Auto-selects SendGrid when SENDGRID_API_KEY is set; otherwise uses the Django
# console backend so local development and tests work without credentials.
# To force a specific backend (e.g. SMTP), set EMAIL_BACKEND explicitly.
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND')
if not EMAIL_BACKEND:
    EMAIL_BACKEND = (
        'tracker.email_backends.SendGridBackend' if SENDGRID_API_KEY
        else 'django.core.mail.backends.console.EmailBackend'
    )

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'DSA Tracker <no-reply@dsatracker.app>')

# Verification / reset token expiry (hours)
EMAIL_VERIFICATION_EXPIRY_HOURS = int(os.environ.get('EMAIL_VERIFICATION_EXPIRY_HOURS', '24'))
PASSWORD_RESET_EXPIRY_HOURS = int(os.environ.get('PASSWORD_RESET_EXPIRY_HOURS', '1'))

# Frontend URL used in verification / reset email links. Keep on one line, no trailing slash.
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_ALWAYS_EAGER', 'False') == 'True'

CELERY_BEAT_SCHEDULE = {
    'daily-review-digest': {
        'task': 'tracker.tasks.send_daily_review_digest',
        'schedule': 86400,  # daily
    },
    'refresh-analytics': {
        'task': 'tracker.tasks.refresh_user_analytics',
        'schedule': 86400,  # daily
    },
    'check-challenge-deadlines': {
        'task': 'tracker.tasks.check_challenge_deadlines',
        'schedule': 300,  # every 5 minutes
    },
    'send-challenge-expiry-reminders': {
        'task': 'tracker.tasks.send_challenge_expiry_reminders',
        'schedule': 300,  # every 5 minutes
    },
    'reset-weekly-points': {
        'task': 'tracker.tasks.reset_weekly_points',
        'schedule': 604800,  # every 7 days (Monday UTC via crontab ideally)
    },
    'seed-achievements': {
        'task': 'tracker.tasks.seed_achievements',
        'schedule': 86400,  # daily — idempotent, ensures new achievements are always present
    },
}
