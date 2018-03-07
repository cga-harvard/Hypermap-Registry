# Hypermap Registry Architecture

## Integration within a Django project

Make sure you have registry module installed inside your working environment and have an elasticsearch version of 2.4.0
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
curl -v "http://(admin_username):(admin_password)@(host)/registry/(catalog)/csw?service=CSW&request=Transaction&version=2.0.2" -d "@(document_body_path)"
```

As an example, using the template found in the data folder,

```
curl -v "http://admin:admin@localhost/registry/hypermap/csw?service=CSW&request=Transaction&version=2.0.2" -d "@data/cswt_insert.xml"
```

Verify that layers have been added into the database.

## Important notes

Please check ```django.env``` file as example.

- ```REGISTRY_MAPPING_PRECISION``` string value, should be around 50m. Very small values (~1m) may cause the search backend to raise Timeout Error in small computers.
- ```REGISTRY_HARVEST_SERVICES``` Boolean value, must be False if CSW transactions are used in order to add layers.
- ```REGISTRY_INDEX_CACHED_LAYERS_PERIOD``` Time value in minutes, should be around 5-10. This variable corresponds the time that layers from cache are indexed into the search backend
- ```REGISTRY_CHECK_PERIOD``` Time in minutes, is the value to perform the check of services. Should be around 30-120.
- ```REGISTRY_LIMIT_LAYERS``` is the highest value that HHypermap Registry will create layers for each service. Set 0 to create all layers from a service.

## Hhypermap registry troubleshootings

**1. When I add an url into the database, services are not created**

  - Verify that database service is ready with migrations.
  - Check that celery process started after database migrations.

**2. Services and layers are created, but layers are not indexed into search backend**

As an administrator, verify in the *periodic tasks* section that index cached layers task is set.

![](https://cloud.githubusercontent.com/assets/54999/18128944/f18219f0-6f4d-11e6-98d3-6dab0a2a37d9.png)

## Performance considerations

The Hypermap architecture depends on 6 main components:


```
+-------------------+      +----------------------+
|                   |      |                      |
|                   |      |    postgres          |
|    django app     <--+--->                      |
|                   |  |   |                      |
|                   |  |   |                      |
+--------^----------+  |   +----------------------+
         |             |
+--------v----------+  |   +----------------------+
|                   |  |   |                      |
|                   |  |   |                      |
|     rabbitmq      |  +--->    elastic search    |
|                   |  |   |                      |
|                   |  |   |                      |
+---------^---------+  |   +----------------------+
          |            |
+---------v--------+   |   +----------------------+
|                  |   |   |                      |
|                  |   |   |                      |
|      celery      <---+--->      memcached       |
|   & celery beats |       |                      |
|                  |       |                      |
+------------------+       +----------------------+
```


If you want to see how to install those services, refer to "Manual Installations" in the developers documentation.

### Django app

The application layer [#TODO: provide more info here]

The app can be hosted via wsgi application located here: `hypermap/wsgi.py` for production enviroment is recommended to host it with uWSGI application server. Refer to https://uwsgi-docs.readthedocs.io/en/latest/ to more documentation.

##### How to start?

##### Development:
```
python manage.py runserver
```

##### Production:
```
uwsgi --module=hypermap.wsgi:application --env DJANGO_SETTINGS_MODULE=hypermap.settings
```
Read more about [Configuring and starting the uWSGI server for Django](https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/uwsgi/#configuring-and-starting-the-uwsgi-server-for-django)

##### Docker:
```
make start
```


### Rabbit MQ, Celery and Memcached

The queue/task layer. It performs operations (as follows above) that works with dedicated async workers that could run in the local or remote machines connected to a Rabbit MQ instance.

 **Harvesting and Indexing**

Download metadata from Internet, each time an Endpoint, Service and Layer is created a worker starts async jobs to fetch the information for the remote services.

**Perform Periodic/Scheduled Tasks (AKA beats)**

Kicks off tasks at regular intervals, two important periodic tasks are placed in the settings file:

Once a Layers are created, and checked with `hypermap.aggregator.tasks.check_all_services` are inserted to Memcached to store a buffer for the task `hypermap.aggregator.tasks.index_cached_layers` where a batch call is made to Search engine in order to index.


***Important settings***

`REGISTRY_CHECK_PERIOD` (in minutes) defines the interval which the task `check_all_services` will be executed by the available workers to start checking the Service and Layers status.

`REGISTRY_INDEX_CACHED_LAYERS_PERIOD` (in minutes) defines the interval which the task `index_cached_layers` will be executed by the available workers to start to send memcached buffered layers to the search backend.

The setting `CELERYBEAT_SCHEDULE` registers the creation of those periodic tasks:

```
CELERYBEAT_SCHEDULE = {
    'Check All Services': {
        'task': 'hypermap.aggregator.tasks.check_all_services',
        'schedule': timedelta(minutes=REGISTRY_CHECK_PERIOD)
    },
    'Index Cached Layers': {
        'task': 'hypermap.aggregator.tasks.index_cached_layers',
        'schedule': timedelta(minutes=REGISTRY_INDEX_CACHED_LAYERS_PERIOD)
    }
}
```

Those 2 periodic tasks should be automatically created in admin site when starting the celery workers. One way to check this is go to the admin site and verify in the "Periodic Tasks" page the presence of 3 tasks:

##### How to start?

```
celery worker --app=hypermap.celeryapp:app --concurrency 4 -B -l INFO
```

##### Docker:
```
make start
```

##### How to check periodic tasks created by Celery?

<img src="http://panchicore.d.pr/kLYB+" width="400">

You have to ensure only a single scheduler is running for a schedule at a time, otherwise you would end up with duplicate tasks. Using a centralized approach means the schedule does not have to be synchronized, and the service can operate without using locks.

**Why `REGISTRY_CHECK_PERIOD` should be an extended period of time**

`check_all_services` performs connections to the registered services in order to make checks and download information, if checks periods are too low it could be causing massive connections to the services and cause high incoming traffic and workload that could looks like a denial of service attack. The recommended setting with `REGISTRY_CHECK_PERIOD` is `60*24` to perform a daily check.

One way to avoid those remote connections to the service servers not required/needed to harvest, is to set `Service.is_monitored=True`.

As in admin site:

<img src="http://panchicore.d.pr/1eC9N+" width="300">

**Workers quantity (--concurrency N)**

The recommended number of concurrent workers running in a machine should be near to the number of CPU cores.

**Scalling up/down: Register celery nodes**

Deploy the hypermap code in a different machine in the same cluster and use the same `BROKER_URL`. Task will be automaticaly starting on this node. Dont start with beats to ensure only a single scheduler is running for a schedule at a time, otherwise you would end up with duplicate tasks.

**Starting celery without beats**

Just remove the `-B` from the start command:

```
celery worker --app=hypermap.celeryapp:app --concurrency 4 -l INFO
```

**How to purge active and pending task from celery**

this is unrecoverable, and the tasks will be deleted from the messaging server.

First stop all workers and run:
```
celery worker --app=hypermap.celeryapp:app purge -f
```


### Elasticsearch

**`REGISTRY_MAPPING_PRECISION`**

This parameter may be used instead of tree_levels to set an appropriate value for the tree_levels parameter. The value specifies the desired precision and Elasticsearch will calculate the best tree_levels value to honor this precision. The value should be a number followed by `m` distance unit.

**Performance considerations**

Elasticsearch uses the paths in the prefix tree as terms in the index and in queries. The higher the levels is (and thus the precision), the more terms are generated. Of course, calculating the terms, keeping them in memory, and storing them on disk all have a price. Especially with higher tree levels, indices can become extremely large even with a modest amount of data. Additionally, the size of the features also matters. Big, complex polygons can take up a lot of space at higher tree levels. Which setting is right depends on the use case. Generally one trades off accuracy against index size and query performance.

The defaults in Elasticsearch for both implementations are a compromise between index size and a reasonable level of precision of 50m at the equator. This allows for indexing tens of millions of shapes without overly bloating the resulting index too much relative to the input size.

So take care settings low `REGISTRY_MAPPING_PRECISION` because at the moment of sending Layers to Elasticsearch it will become slow.
