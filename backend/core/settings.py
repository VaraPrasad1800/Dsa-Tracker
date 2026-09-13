import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

IS_TESTING = 'test' in sys.argv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dsa-tracker-local-dev-secret-key-replace-in-prod')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '*').split(',') if h.strip()]

# Production security hardening
if not DEBUG:
    SECURE_SSL_REDIRECT = (os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true') and not IS_TESTING
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
    'drf_spectacular',
    'corsheaders',
    'django_filters',
    # Local apps
    'tracker',
]

MIDDLEWARE = [
    'tracker.middleware.RequestIDMiddleware',
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
if os.environ.get('POSTGRES_DB') and not IS_TESTING and os.environ.get('USE_SQLITE') != 'True':
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
            'NAME': BASE_DIR / os.environ.get('SQLITE_DB_NAME', 'db.sqlite3'),
        }
    }

# Cache Configuration: Redis with LocMemCache fallback
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL and not IS_TESTING:
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

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Production: set CORS_ALLOWED_ORIGINS to a comma-separated list of allowed
# frontend origins, e.g. CORS_ALLOWED_ORIGINS=https://your-app.vercel.app
#
# Development: leave unset → CORS_ALLOW_ALL_ORIGINS = True (safe locally).
# ---------------------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True

_cors_origins_env = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()
if _cors_origins_env:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_env.split(',') if o.strip()]
else:
    CORS_ALLOW_ALL_ORIGINS = True  # dev fallback — always set in production

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
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '120/hour',
        'judge_run': '20/min',
        'judge_submit': '10/min',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# OpenAPI / Swagger Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'DSA Tracker API',
    'DESCRIPTION': 'Production-grade API for DSA Tracker — algorithmic problem bank, online judge, Leitner spaced repetition, and behavioral analytics.',
    'VERSION': 'v1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '1'))
JWT_REFRESH_EXPIRATION_HOURS = int(os.environ.get('JWT_REFRESH_EXPIRATION_HOURS', '168'))  # 7 days

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'tracker': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Email configuration (SendGrid in production, console fallback for dev/test)
# Auto-selects SendGrid when SENDGRID_API_KEY is set; otherwise uses the Django
# console backend so local development and tests work without credentials.
# In production (DEBUG=False), ALWAYS requires SendGridBackend.
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '').strip()
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND')
if not EMAIL_BACKEND:
    if not DEBUG:
        # In production, NEVER silently fall back to console backend
        EMAIL_BACKEND = 'tracker.email_backends.SendGridBackend'
    else:
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
CELERY_TASK_ALWAYS_EAGER = True if IS_TESTING else (os.environ.get('CELERY_ALWAYS_EAGER', 'False') == 'True')

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

# Logging configuration with request_id support
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_id': {
            '()': 'tracker.middleware.RequestIDFilter',
        },
    },
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['request_id'],
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
    },
}

# Sentry error tracking & APM (initialized only if SENTRY_DSN is provided)
SENTRY_DSN = os.environ.get('SENTRY_DSN', '').strip()
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1' if not DEBUG else '0.0')),
        send_default_pii=False,
        environment=os.environ.get('DJANGO_ENV', 'production' if not DEBUG else 'development'),
    )

