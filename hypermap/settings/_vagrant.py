from .default import *  # noqa
from .default import MIDDLEWARE_CLASSES
from .default import INSTALLED_APPS
import os


SITE_URL = 'http://192.168.33.15:8000/'

SEARCH_ENABLED = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('DATABASE_NAME', 'hypermap'),
        'USER': os.getenv('DATABASE_USER', 'hypermap'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'hypermap'),
        'HOST': os.getenv('DATABASE_HOST', '127.0.0.1'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    }
}

# setup for developer toolbar
DEBUG_TOOLBAR_PATCH_SETTINGS = False

INSTALLED_APPS = INSTALLED_APPS + (
    'debug_toolbar',
)

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INTERNAL_IPS = ('192.168.33.1',)

# Load more settings from a file called local_settings.py if it exists
try:
    from local_settings import *  # noqa
except ImportError:
    pass
