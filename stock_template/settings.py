import os
import redis
from pathlib import Path

#Base directory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#Server seting.
SITE_URL = 'http://127.0.0.1:8000'
STATIC_URL = '/static/back/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
STATIC_ROOT = os.path.join(BASE_DIR, 'deploy_static/')
SECRET_KEY = "django-insecure-emr=&oo%%y-hy6=)7n)^#+knef@u^$&^c3*j8-g=**qh@--)if"
ROUTER_INCLUDE_ROOT_VIEW = False

MEDIA_PRIVATE_ROOT = os.path.join(BASE_DIR, 'media_private/')
STREAM_ROOT = os.path.join(BASE_DIR, 'stream_private/s1/')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
AUTH_USER_MODEL = 'account.Account'

AUTHENTICATION_BACKENDS = [
    'account.authenticate.EmailModelBackend',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
    'rest_framework',
    'rest_framework_simplejwt',
    "rest_framework_swagger",
    
    "account",
    "log",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "stock_template.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = 'stock_template.wsgi.application'
ASGI_APPLICATION = 'stock_template.routing.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('redis', 6379)],
        },
    },
}

# MODEL
PASSWORD_MIN = 4

# Swagger settings
SWAGGER_SETTINGS = {
    'IS_ENABLE': True,
    'SHOW_REQUEST_HEADERS': True,
    'IS_SUPERUSER': True,
    'VALIDATOR_URL': None,
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        # 'BACKEND': 'django_prometheus.cache.backends.memcachedched.MemcachedCache',  # ENABLED CACHES METRICS
        'LOCATION': 'memcached',
    }
}

FCM_DJANGO_SETTINGS = {
    "FCM_SERVER_KEY": 'AIzaSyCMCQ8VdR-k5uy4jrVvssYUDZxGUm7w_DA',
    "ONE_DEVICE_PER_USER": False,
    "DELETE_INACTIVE_DEVICES": False,
}

X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Internationalization setting
# https://docs.djangoproject.com/en/1.11/topics/i18n/
## Time zone setting

TIME_ZONE = 'Asia/Bangkok'

## Datetime format setting
DATE_FORMAT = '%d %b %Y'
DATE_FORMAT_INDEX = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
DATETIME_FORMAT = '%e %B %Y %H:%M:%S'
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

## Language setting
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True

## Front encoding.
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Cached settings
## Redis
REDIS = redis.Redis('redis')
RESULT_BACKEND = 'redis://redis:6379/0'

## CELERY
CELERY_BROKER_URL = 'amqp://rabbitmq:5672'
CELERY_ACKS_LATE = True
FLOWER_PROXY = 'http://127.0.0.1:5555/'
RABBIT_MANAGEMENT_PROXY_URL = 'http://rabbitmq:15672/'

CELERY_TIMEZONE = TIME_ZONE
CELERYD_PREFETCH_MULTIPLIER = 1

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "mydatabase",
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

#REST_Framwork_setting
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'utils.rest_framework.pagination.CustomPagination',
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'utils.rest_framework.exception.exception_handler',

    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer'
    ),

    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.MultiPartRenderer',
        'rest_framework.renderers.JSONRenderer',
    ),
    'PAGE_SIZE': 24,
    # "DATE_INPUT_FORMATS": ["%d/%m/%Y"],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
}


# logging
LOGGING_MAXBYTES = 1024 * 1024 * 1024  # File size 1GB
LOGGING_BACKUPCOUNT = 10  # x Backup 10 files
LOGGING_INTERVAL = 1  # Every 1 Days
LOGGING_FILE_LOCATION = '/backups/'  # Path log file
LOGGING_LIMIT_TEXT_RESPONSE = 500
ENABLE_LOGGING = False
LOG_CONFIG = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] %(levelname)s|%(name)s|%(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'celery': {
            'format': '[%(asctime)s] %(levelname)s|%(name)s|%(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/backups/app.log',  # need to have /backups/ dir if don't can't runserver
            'maxBytes': 1024 * 1024 * 1024,
            'backupCount': 2,
            'formatter': 'simple',
        },
        'celery_console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'celery'
        },
        'celery_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/backups/celery.log',  # need to have /backups/ dir if don't can't runserver
            'maxBytes': 1024 * 1024 * 1024,
            'backupCount': 2,
            'formatter': 'celery',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['celery_console', 'celery_file'],
            'level': 'INFO',
            'propagate': False,
        }
    }
}

# Testing setting ()
ENABLE_LOGGING = False
CELERY_TASK_ALWAYS_EAGER = True
MONGODB_HOST = '127.0.0.1'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
CACHES['default'] = {'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }
FCM_DJANGO_SETTINGS["FCM_SERVER_KEY"] = 'AIzaSyCMCQ8VdR-k5uy4jrVvssYUDZxGUm7w_DA'