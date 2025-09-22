"""
Production settings for PriceScan API
"""
import os
from .settings import *

# Override settings for production
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'pricescan_db'),
        'USER': os.environ.get('POSTGRES_USER', 'pricescan_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'pricescan_password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db_pricescan'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        }
    }
}

# Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Static files
STATIC_ROOT = '/app/staticfiles'
MEDIA_ROOT = '/app/media'

# Email settings (if needed)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Monitoring
PROMETHEUS_ENABLED = os.environ.get('PROMETHEUS_ENABLED', 'False').lower() == 'true'
GRAFANA_ENABLED = os.environ.get('GRAFANA_ENABLED', 'False').lower() == 'true'

# Performance
CACHE_TTL = int(os.environ.get('CACHE_TTL', '300'))
RATE_LIMIT_ANON = int(os.environ.get('RATE_LIMIT_ANON', '100'))
RATE_LIMIT_USER = int(os.environ.get('RATE_LIMIT_USER', '1000'))

# Parsers
PARSER_TIMEOUT = int(os.environ.get('PARSER_TIMEOUT', '300'))
PARSER_MAX_RETRIES = int(os.environ.get('PARSER_MAX_RETRIES', '3'))
PARSER_RETRY_DELAY = int(os.environ.get('PARSER_RETRY_DELAY', '60'))

# Alerts
ALERT_CHECK_INTERVAL = int(os.environ.get('ALERT_CHECK_INTERVAL', '300'))
ALERT_CLEANUP_DAYS = int(os.environ.get('ALERT_CLEANUP_DAYS', '30'))

