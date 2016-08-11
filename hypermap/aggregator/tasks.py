from __future__ import absolute_import

from django.conf import settings

from celery import shared_task

REGISTRY_LIMIT_LAYERS = getattr(settings, 'REGISTRY_LIMIT_LAYERS', -1)
REGISTRY_SEARCH_URL = getattr(settings, 'REGISTRY_SEARCH_URL', None)

if REGISTRY_SEARCH_URL is None:
    SEARCH_ENABLED = False
    SEARCH_TYPE = None
    SEARCH_URL = None
else:
    SEARCH_ENABLED = True
    SEARCH_TYPE = REGISTRY_SEARCH_URL.split('+')[0]
    SEARCH_URL = REGISTRY_SEARCH_URL.split('+')[1]


if REGISTRY_LIMIT_LAYERS > 0:
    DEBUG_SERVICES = True
    DEBUG_LAYERS_NUMBER = REGISTRY_LIMIT_LAYERS
else:
    DEBUG_SERVICES = False
    DEBUG_LAYERS_NUMBER = -1


@shared_task(bind=True)
def check_all_services(self):
    from hypermap.aggregator.models import Service
    service_to_processes = Service.objects.filter(active=True)
    total = service_to_processes.count()
    count = 0
    for service in service_to_processes:
        # update state
        if not self.request.called_directly:
            self.update_state(
                state='PROGRESS',
                meta={'current': count, 'total': total}
            )
        check_service.delay(service)
        count = count + 1


@shared_task(bind=True)
def check_service(self, service):
    # total is determined (and updated) exactly after service.update_layers
    total = 100

    def status_update(count):
        if not self.request.called_directly:
            self.update_state(
                state='PROGRESS',
                meta={'current': count, 'total': total}
            )

    status_update(0)
    service.update_layers()
    service.index_layers()
    # we count 1 for update_layers and 1 for service check for simplicity
    layer_to_process = service.layer_set.all()

    if DEBUG_SERVICES:
        layer_to_process = layer_to_process[0:DEBUG_LAYERS_NUMBER]

    total = layer_to_process.count() + 2
    status_update(1)
    service.check_available()
    status_update(2)
    count = 3

    if not settings.REGISTRY_SKIP_CELERY:
        for layer in layer_to_process:
            # update state
            status_update(count)
            check_layer.delay(layer)
            count += 1
    else:
        for layer in layer_to_process:
            status_update(count)
            check_layer(layer)
            count += 1


@shared_task(bind=True, time_limit=10)
def check_layer(self, layer):
    print 'Checking layer %s' % layer.name
    success, message = layer.check_available()
    # every time a layer is checked it should be indexed
    if success and SEARCH_ENABLED:
        if not settings.REGISTRY_SKIP_CELERY:
            index_layer.delay(layer)
        else:
            index_layer(layer)
    if not success:
        from hypermap.aggregator.models import TaskError
        task_error = TaskError(
            task_name=self.name,
            args=layer.id,
            message=message
        )
        task_error.save()


@shared_task(name="clear_index")
def clear_index():
    if SEARCH_TYPE == 'solr':
        print 'Clearing the solr core and indexes'
        from hypermap.aggregator.solr import SolrHypermap
        solrobject = SolrHypermap()
        solrobject.clear_solr()
    elif SEARCH_TYPE == 'elasticsearch':
        print 'Clearing the ES indexes'
        from hypermap.aggregator.elasticsearch_client import ESHypermap
        esobject = ESHypermap()
        esobject.clear_es()


@shared_task(bind=True)
def remove_service_checks(self, service):

    service.check_set.all().delete()

    def status_update(count, total):
        if not self.request.called_directly:
            self.update_state(
                state='PROGRESS',
                meta={'current': count, 'total': total}
            )

    layer_to_process = service.layer_set.all()
    count = 0
    total = layer_to_process.count()
    for layer in layer_to_process:
        # update state
        status_update(count, total)
        layer.check_set.all().delete()
        count = count + 1


@shared_task(bind=True)
def index_service(self, service):

    layer_to_process = service.layer_set.all()
    total = layer_to_process.count()

    def status_update(count):
        if not self.request.called_directly:
            self.update_state(
                state='PROGRESS',
                meta={'current': count, 'total': total}
            )

    count = 0
    for layer in layer_to_process:
        # update state
        status_update(count)
        if not settings.REGISTRY_SKIP_CELERY:
            index_layer.delay(layer)
        else:
            index_layer(layer)
        count = count + 1


@shared_task(bind=True)
def index_layer(self, layer):
    # TODO: Make this function more DRY
    # by abstracting the common bits.
    if SEARCH_TYPE == 'solr':
        from hypermap.aggregator.solr import SolrHypermap
        print 'Syncing layer %s to solr' % layer.name
        try:
            solrobject = SolrHypermap()
            success, message = solrobject.layer_to_solr(layer)
            if not success:
                from hypermap.aggregator.models import TaskError
                task_error = TaskError(
                    task_name=self.name,
                    args=layer.id,
                    message=message
                )
                task_error.save()
        except:
            print 'There was an exception here!'
            self.retry(layer)
    elif SEARCH_TYPE == 'elasticsearch':
        from hypermap.aggregator.elasticsearch_client import ESHypermap
        print 'Syncing layer %s to es' % layer.name
        esobject = ESHypermap()
        success, message = esobject.layer_to_es(layer)
        if not success:
            from hypermap.aggregator.models import TaskError
            task_error = TaskError(
                task_name=self.name,
                args=layer.id,
                message=message
            )
            task_error.save()


@shared_task(bind=True)
def index_all_layers(self):
    from hypermap.aggregator.models import Layer

    layer_to_processes = Layer.objects.all()
    total = layer_to_processes.count()
    count = 0
    for layer in Layer.objects.all():
        # update state
        if not self.request.called_directly:
            self.update_state(
                state='PROGRESS',
                meta={'current': count, 'total': total}
            )
        if not settings.REGISTRY_SKIP_CELERY:
            index_layer.delay(layer)
        else:
            index_layer(layer)
        count = count + 1


@shared_task(bind=True)
def update_endpoint(self, endpoint, greedy_opt=False):
    from hypermap.aggregator.utils import create_services_from_endpoint
    from hypermap.aggregator.models import Endpoint

    print 'Processing endpoint with id %s: %s' % (endpoint.id, endpoint.url)

    # Override the greedy_opt var with the value from the endpoint list
    # if it's available.
    if endpoint.endpoint_list:
        greedy_opt = endpoint.endpoint_list.greedy

    imported, message = create_services_from_endpoint(endpoint.url, greedy_opt=greedy_opt, catalog=endpoint.catalog)

    # this update will not execute the endpoint_post_save signal.
    Endpoint.objects.filter(id=endpoint.id).update(
        imported=imported, message=message, processed=True
    )


@shared_task(bind=True)
def update_endpoints(self, endpoint_list):
    # for now we process the enpoint even if they were already processed
    endpoint_to_process = endpoint_list.endpoint_set.filter(processed=False)
    total = endpoint_to_process.count()
    count = 0
    if not settings.REGISTRY_SKIP_CELERY:
        for endpoint in endpoint_to_process:
            update_endpoint.delay(endpoint)
        # update state
        if not self.request.called_directly:
            self.update_state(
                state='PROGRESS',
                meta={'current': count, 'total': total}
            )
    else:
        for endpoint in endpoint_to_process:
            update_endpoint(endpoint)

    return True
