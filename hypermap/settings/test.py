from .default import *  # noqa

SKIP_CELERY_TASK = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

SOLR_ENABLED = True
SOLR_URL = 'http://localhost:8983/solr/hypermap_test'

# BROKER_BACKEND = 'memory'
# BROKER_URL='memory://'
# CELERY_ALWAYS_EAGER = True
# CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
# TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
