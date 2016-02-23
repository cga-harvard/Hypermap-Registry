from settings.default import *  # noqa

SOLR_ENABLED = False
SOLR_URL = "http://solr:8983/solr/search"

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
