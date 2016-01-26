from settings.default import *  # noqa

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
