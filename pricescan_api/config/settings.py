import os
from datetime import timedelta
from pathlib import Path

from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", default=get_random_secret_key())

DEBUG = os.environ.get("DEBUG", "True").lower() in {"true", "1", "yes", "on"}

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
# ALLOWED_HOSTS = ["*"]

BOT_SERVICE_TOKEN = os.getenv("BOT_SERVICE_TOKEN")


# Application definition
INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "django_redis",
    "django_celery_beat",
    "import_export",
    "celery",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    # Local apps
    "user",
    "product",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
        "PAGE_SIZE": 5,
        "MAX_PAGE_SIZE": 20
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}
# -------Database for local-------
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379/1",
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         }
#     }
# }
# CELERY_BROKER_URL = "redis://localhost:6379/1"
# CELERY_RESULT_BACKEND = "disabled"

# # -------Database for docker-------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "pricescan_db"),
        "USER": os.getenv("POSTGRES_USER", "pricescan_user"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "pricescan_password"),
        "HOST": os.getenv("POSTGRES_HOST", "db_pricescan"),
        "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION":  os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")


CELERY_TASK_RESULT_EXPIRES = 28800

# -------Password validation-------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# -------Internationalization-------

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True

AUTH_USER_MODEL = "user.User"

# -------Static files (CSS, JavaScript, Images)-------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "collected_static"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# -------Default primary key field type-------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------Celery-------
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 100
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "max_retries": 10,
    "interval_start": 0.1,
    "interval_step": 0.2,
    "interval_max": 1.0,
    "retry_on_timeout": True,
    "health_check_interval": 10,
    "socket_keepalive": True,
}

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"


SPECTACULAR_SETTINGS = {
    "TITLE": "PriceScan API",
    # "DESCRIPTION": "Поиск и сравнение цен
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
        "SECURITY_SCHEMES": {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        "ServiceToken": {"type": "apiKey", "in": "header", "name": "X-Service-Token"},
    },
    "SECURITY": [{"BearerAuth": []}],  # глобально — JWT
}

# Logging
LOG_FOLDER = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_FOLDER, "project.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "user": {  # -------Новый handler для пользователей-------
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_FOLDER, "user.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "product": {  # -------Новый handler для продуктов-------
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_FOLDER, "product.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "parser_results": {  # -------Новый handler для парсинга-------
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_FOLDER, "parser_results.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "failed_requests": {  # -------Новый handler для неудачных запросов-------
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_FOLDER, "failed_requests.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "user": {
            "handlers": ["user", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "product": {
            "handlers": ["product", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "parser_results": {
            "handlers": ["parser_results", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "failed_requests": {
            "handlers": ["failed_requests", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.beat": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.worker": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
