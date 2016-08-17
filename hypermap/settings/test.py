from .default import *  # noqa
from .default import BASE_DIR
import os

REGISTRY_SKIP_CELERY = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

SOLR_ENABLED = True
REGISTRY_SEARCH_URL = os.getenv('REGISTRY_SEARCH_URL', "elasticsearch+http://localhost:9200")

# BROKER_BACKEND = 'memory'
# BROKER_URL='memory://'
# CELERY_ALWAYS_EAGER = True
# CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
# TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
