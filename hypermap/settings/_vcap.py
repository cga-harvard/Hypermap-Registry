import dj_database_url
import json
import os
from settings.default import *

vcap_config = os.environ.get('VCAP_SERVICES')
decoded_config = json.loads(vcap_config)

DEBUG = False
SITE_URL = os.environ['application_uris'][0]
ALLOWED_HOSTS = [SITE_URL, 'localhost']

DATABASES = {'default': dj_database_url.config()}

BROKER_URL = decoded_config['cloudamqp'][0]['credentials']['uri']

SEARCH_ENABLED = True
SEARCH_TYPE = 'elasticsearch'
SEARCH_URL = decoded_config['searchly'][0]['credentials']['sslUri']

SKIP_CELERY_TASK = True

PYCSW['server']['url'] = SITE_URL + 'csw'
