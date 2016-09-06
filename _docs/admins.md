# Hypermap Registry for administrators

## Integration within a Django project

Make sure you have registry module installed inside your working environment.
```
pip install django-registry
```

Add this variables into your settings.py

```python
from hypermap.settings import REGISTRY_PYCSW

REGISTRY = True # ensure the value is True
REGISTRY_SKIP_CELERY = False
REGISTRY_SEARCH_URL = os.getenv('REGISTRY_SEARCH_URL',
                                'elasticsearch+%s' % ES_URL)

# Check layers every 24 hours
REGISTRY_CHECK_PERIOD = int(os.environ.get('REGISTRY_CHECK_PERIOD', '1440'))
# Index cached layers every minute
REGISTRY_INDEX_CACHED_LAYERS_PERIOD = int(os.environ.get('REGISTRY_CHECK_PERIOD', '1'))

CELERYBEAT_SCHEDULE = {
    'Check All Services': {
        'task': 'check_all_services',
        'schedule': timedelta(minutes=REGISTRY_CHECK_PERIOD)
    },
    'Index Cached Layers': {
        'task': 'hypermap.aggregator.tasks.index_cached_layers',
        'schedule': timedelta(minutes=REGISTRY_INDEX_CACHED_LAYERS_PERIOD)
    }
}

# -1 Disables limit.
REGISTRY_LIMIT_LAYERS = int(os.getenv('REGISTRY_LIMIT_LAYERS', '-1'))

FILE_CACHE_DIRECTORY = '/tmp/mapproxy/'
REGISTRY_MAPPING_PRECISION = os.getenv('REGISTRY_MAPPING_PRECISION', '500m')

# if DEBUG_SERVICES is set to True, only first DEBUG_LAYERS_NUMBER layers
# for each service are updated and checked
REGISTRY_PYCSW['server']['url'] = SITE_URL.rstrip('/') + '/registry/search/csw'

REGISTRY_PYCSW['metadata:main'] = {
    'identification_title': 'Registry Catalogue',
    'identification_abstract': 'Registry, a Harvard Hypermap project, is an application that manages ' \
    'OWS, Esri REST, and other types of map service harvesting, and maintains uptime statistics for ' \
    'services and layers.',
    'identification_keywords': 'sdi,catalogue,discovery,metadata,registry,HHypermap',
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
    'contact_role': 'Point of Contact'
}
```
Add the following django applications into the main project INSTALLED_APPS settings.

```
'djmp',
'hypermap.aggregator',
'hypermap.dynasty',
'hypermap.search',
'hypermap.search_api',
'rest_framework',
```

## Test CSW transactions

```
curl -v "http://admin:admin@localhost/registry/hypermap/csw/?service=CSW&request=Transaction&version=2.0.2" -d "@data/cswt_insert.xml"
```

Verify that layers have been added into the database.



