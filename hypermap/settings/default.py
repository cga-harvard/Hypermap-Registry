"""
Django settings for hypermap project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import os.path
import sys
from datetime import timedelta


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DJANGO_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
PROJECT_DIR = os.path.abspath(os.path.join(DJANGO_DIR, os.pardir))

BASE_URL = os.getenv('BASE_URL', 'localhost')
BASE_PORT = os.getenv('BASE_PORT', '8000')

SITE_URL = 'http://%s:%s' % (BASE_URL, BASE_PORT)

ALLOWED_HOSTS = [BASE_URL, ]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'mc0+7x(mor+4-acs$m-w6qj(i&^*6uiyb+6v^)i4w(fo*8qgu5'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

SEARCH_ENABLED = os.getenv(str2bool('SEARCH_ENABLED'), False)
SEARCH_TYPE = 'solr'
SEARCH_URL = os.getenv('SEARCH_URL', 'http://127.0.0.1:8983/solr/search')

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'djcelery',
    'polymorphic',
    'pagination',
    'taggit',
    'django_extensions',
    'djmp',
    'maploom_registry',
    'hypermap.aggregator',
    'hypermap.dynasty',
    'hypermap.search',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pagination.middleware.PaginationMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.static',
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    'hypermap.context_processors.resource_urls',
)

ROOT_URLCONF = 'hypermap.urls'

WSGI_APPLICATION = 'hypermap.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DATABASE_NAME', 'development.db'),
        'USER': os.getenv('DATABASE_USER', 'hypermap'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'hypermap'),
        'HOST': os.getenv('DATABASE_HOST', '127.0.0.1'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# media files
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')
MEDIA_URL = '/media/'

MAPPROXY_CONFIG = os.path.join(MEDIA_ROOT, 'mapproxy_config')

# Celery and RabbitMQ stuff
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_RESULT_BACKEND = 'cache+memcached://127.0.0.1:11211/'
CELERYD_PREFETCH_MULTIPLIER = 25

CELERYBEAT_SCHEDULE = {
    'Check All Services': {
        'task': 'check_all_services',
        'schedule': timedelta(minutes=15)
    },
}

CELERY_TIMEZONE = 'UTC'
BROKER_URL = os.getenv('BROKER_URL', 'amqp://guest:guest@localhost:5672//')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level': 'ERROR',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR', 'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'celery': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"], "level": "ERROR", },
        "hypermap": {
            "handlers": ["console"], "level": "INFO", },
        "owslib": {
            "handlers": ["console"], "level": "ERROR", },
        "celery": {
            "handlers": ["console"], "level": "DEBUG", },
        "pycsw": {
            "handlers": ["console"], "level": "ERROR", },
        }
    }

# we need to get rid of this once we figure out how to bypass the broker in tests
SKIP_CELERY_TASK = os.getenv(str2bool('SKIP_CELERY_TASK'), False)

# taggit
TAGGIT_CASE_INSENSITIVE = True

# WorldMap Service credentials (override this in local_settings or _ubuntu in production)
WM_USERNAME = os.getenv('WM_USERNAME', 'hypermap')
WM_PASSWORD = os.getenv('WM_PASSWORD', 'secret')

# pycsw settings
PYCSW = {
    'server': {
        # 'home': '.',
        'url': '%s/search/csw' % SITE_URL.rstrip('/'),
        'encoding': 'UTF-8',
        'language': LANGUAGE_CODE,
        'maxrecords': '10',
        'pretty_print': 'true',
        # 'domainquerytype': 'range',
        'domaincounts': 'true',
        'profiles': 'apiso'
    },
    'manager': {
        # authentication/authorization is handled by Django
        'transactions': 'false',
        'allowed_ips': '*',
        # 'csw_harvest_pagesize=10',
    },
    'repository': {
        'source': 'HHypermap',
        'mappings': os.path.join(os.path.dirname(__file__), '..', 'search', 'pycsw_local_mappings.py')
    },
    'metadata:main': {
        'identification_title': 'HHypermap Catalogue',
        'identification_abstract': 'HHypermap (Harvard Hypermap) Supervisor is an application that manages ' \
        'OWS, Esri REST, and other types of map service harvesting, and maintains uptime statistics for ' \
        'services and layers.',
        'identification_keywords': 'sdi,catalogue,discovery,metadata,HHypermap',
        'identification_keywords_type': 'theme',
        'identification_fees': 'None',
        'identification_accessconstraints': 'None',
        'provider_name': 'Organization Name',
        'provider_url': SITE_URL,
        'contact_name': 'Lastname, Firstname',
        'contact_position': 'Position Title',
        'contact_address': 'Mailing Address',
        'contact_city': 'City',
        'contact_stateorprovince': 'Administrative Area',
        'contact_postalcode': 'Zip or Postal Code',
        'contact_country': 'Country',
        'contact_phone': '+xx-xxx-xxx-xxxx',
        'contact_fax': '+xx-xxx-xxx-xxxx',
        'contact_email': 'Email Address',
        'contact_url': 'Contact URL',
        'contact_hours': 'Hours of Service',
        'contact_instructions': 'During hours of service. Off on weekends.',
        'contact_role': 'pointOfContact'
    }
}
