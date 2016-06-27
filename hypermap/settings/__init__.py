import dj_database_url
import json
from .default import *  # noqa

#####

CLOUD_FOUNDRY = os.getenv('CLOUD_FOUNDRY', None)

if CLOUD_FOUNDRY is not None:
    vcap_service_config = os.environ.get('VCAP_SERVICES')
    decoded_config = json.loads(vcap_service_config)

    vcap_app_config = os.environ.get('VCAP_APPLICATION')
    # TODO: Get from environment and don't hardcode
    DATABASES = {'default': dj_database_url.config()}

    # use redis
    if 'rediscloud' in decoded_config:
        BROKER_DB = 0
        BROKER_URL = 'redis://:{0}@{1}:{2}/{3}'.format(
            decoded_config['rediscloud'][0]["credentials"]["password"],
            decoded_config['rediscloud'][0]["credentials"]["hostname"],
            decoded_config['rediscloud'][0]["credentials"]["port"],
            BROKER_DB
        )

    # use rabbit
    if 'cloudamqp' in decoded_config:
        BROKER_URL = decoded_config['cloudamqp'][0]['credentials']['uri']

    print "BROKER_URL is {0}".format(BROKER_URL)

    SEARCH_ENABLED = True
    SEARCH_TYPE = 'elasticsearch'
    SEARCH_URL = decoded_config['searchly'][0]['credentials']['sslUri']

    SKIP_CELERY_TASK = False
    PYCSW['server']['url'] = '%s/search/csw' % SITE_URL.rstrip('/')
    PYCSW['metadata:main']['provider_url'] = SITE_URL
