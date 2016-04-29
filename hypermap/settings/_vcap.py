import dj_database_url
import json
import os
from settings.default import *

vcap_service_config = os.environ.get('VCAP_SERVICES')
decoded_config = json.loads(vcap_service_config)

DEBUG = False
vcap_app_config = os.environ.get('VCAP_APPLICATION')
#TODO: Get from environment and don't hardcode
SITE_URL = 'hypermap-demo.cfapps.io'

ALLOWED_HOSTS = [SITE_URL, 'localhost']

DATABASES = {'default': dj_database_url.config()}

BROKER_DB = 0
BROKER_URL = 'redis://:{0}@{1}:{2}/{3}'.format(
    decoded_config['rediscloud'][0]["credentials"]["password"],
    decoded_config['rediscloud'][0]["credentials"]["hostname"],
    decoded_config['rediscloud'][0]["credentials"]["port"],
    BROKER_DB
)

SEARCH_ENABLED = True
SEARCH_TYPE = 'elasticsearch'
SEARCH_URL = decoded_config['searchly'][0]['credentials']['sslUri']

SKIP_CELERY_TASK = True

PYCSW['server']['url'] = 'http://' + SITE_URL + '/csw'
