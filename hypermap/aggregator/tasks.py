from __future__ import absolute_import

import logging

from celery import shared_task, states
from celery.exceptions import Ignore

from django.conf import settings
from django.core.cache import cache


LOGGER = logging.getLogger(__name__)

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
    for service in service_to_processes:
        check_service.delay(service.id)


@shared_task(bind=True)
def check_service(self, service_id):
    from hypermap.aggregator.models import Service
    service = Service.objects.get(pk=service_id)

    # 1. update layers and check service
    if getattr(settings, 'REGISTRY_HARVEST_SERVICES', True):
        service.update_layers()

    layer_to_process = service.layer_set.all()
    if DEBUG_SERVICES:
        layer_to_process = layer_to_process[0:DEBUG_LAYERS_NUMBER]

    service.check_available()

    # 2. check layers if the service is monitored and the layer is monitored
    if service.is_monitored:
        for layer in layer_to_process:
            if layer.is_monitored:
                if not settings.REGISTRY_SKIP_CELERY:
                    check_layer.delay(layer.id)
                else:
                    check_layer(layer.id)

    # 3. index layers
    if getattr(settings, 'REGISTRY_HARVEST_SERVICES', True):
        if not settings.REGISTRY_SKIP_CELERY:
            index_service.delay(service.id)
        else:
            index_service(service.id)


@shared_task(bind=True, soft_time_limit=10)
def check_layer(self, layer_id):
    from hypermap.aggregator.models import Layer
    layer = Layer.objects.get(pk=layer_id)
    LOGGER.debug('Checking layer %s' % layer.name)
    success, message = layer.check_available()
    # every time a layer is checked it should be indexed
    # for now we remove indexing but we do it using a scheduled task unless SKIP_CELERY_TASK
    if success and SEARCH_ENABLED:
        if settings.REGISTRY_SKIP_CELERY:
            index_layer(layer.id)
        else:
            index_layer(layer.id, use_cache=True)


@shared_task(bind=True)
def index_cached_layers(self):
    """
    Index and unindex all layers in the Django cache (Index all layers who have been checked).
    """
    from hypermap.aggregator.models import Layer

    if SEARCH_TYPE == 'solr':
        from hypermap.aggregator.solr import SolrHypermap
        solrobject = SolrHypermap()
    else:
        from hypermap.aggregator.elasticsearch_client import ESHypermap
        from elasticsearch import helpers
        es_client = ESHypermap()

    layers_cache = cache.get('layers')
    deleted_layers_cache = cache.get('deleted_layers')

    # 1. added layers cache
    if layers_cache:
        layers_list = list(layers_cache)
        LOGGER.debug('There are %s layers in cache: %s' % (len(layers_list), layers_list))

        batch_size = settings.REGISTRY_SEARCH_BATCH_SIZE
        batch_lists = [layers_list[i:i+batch_size] for i in range(0, len(layers_list), batch_size)]

        for batch_list_ids in batch_lists:
            layers = Layer.objects.filter(id__in=batch_list_ids)

            if batch_size > len(layers):
                batch_size = len(layers)

            LOGGER.debug('Syncing %s/%s layers to %s: %s' % (batch_size, len(layers_cache), layers, SEARCH_TYPE))

            try:
                # SOLR
                if SEARCH_TYPE == 'solr':
                    success, layers_errors_ids = solrobject.layers_to_solr(layers)
                    if success:
                        # remove layers from cache here
                        layers_cache = layers_cache.difference(set(batch_list_ids))
                        LOGGER.debug('Removing layers with id %s from cache' % batch_list_ids)
                        cache.set('layers', layers_cache)
                # ES
                elif SEARCH_TYPE == 'elasticsearch':
                    with_bulk, success = True, False
                    layers_to_index = [es_client.layer_to_es(layer, with_bulk) for layer in layers]
                    message = helpers.bulk(es_client.es, layers_to_index)

                    # Check that all layers where indexed...if not, don't clear cache.
                    # TODO: Check why es does not index all layers at first.
                    len_indexed_layers = message[0]
                    if len_indexed_layers == len(layers):
                        LOGGER.debug('%d layers indexed successfully' % (len_indexed_layers))
                        success = True
                    if success:
                        # remove layers from cache here
                        layers_cache = layers_cache.difference(set(batch_list_ids))
                        cache.set('layers', layers_cache)
                else:
                    raise Exception("Incorrect SEARCH_TYPE=%s" % SEARCH_TYPE)
            except Exception as e:
                LOGGER.error('Layers were NOT indexed correctly')
                LOGGER.error(e, exc_info=True)
    else:
        LOGGER.debug('No cached layers to add in search engine.')

    # 2. deleted layers cache
    if deleted_layers_cache:
        layers_list = list(deleted_layers_cache)
        LOGGER.debug('There are %s layers in cache for deleting: %s' % (len(layers_list), layers_list))
        # TODO implement me: batch layer index deletion
        for layer_id in layers_list:
            # SOLR
            if SEARCH_TYPE == 'solr':
                if Layer.objects.filter(pk=layer_id).exists():
                    layer = Layer.objects.get(id=layer_id)
                    unindex_layer(layer.id, use_cache=False)
                    deleted_layers_cache = deleted_layers_cache.difference(set([layer_id]))
                    cache.set('deleted_layers', deleted_layers_cache)
            else:
                # TODO implement me
                raise NotImplementedError
    else:
        LOGGER.debug('No cached layers to remove in search engine.')


@shared_task(name="clear_index")
def clear_index():
    if SEARCH_TYPE == 'solr':
        LOGGER.debug('Clearing the solr indexes')
        from hypermap.aggregator.solr import SolrHypermap
        solrobject = SolrHypermap()
        solrobject.clear_solr()
    elif SEARCH_TYPE == 'elasticsearch':
        LOGGER.debug('Clearing the ES indexes')
        from hypermap.aggregator.elasticsearch_client import ESHypermap
        esobject = ESHypermap()
        esobject.clear_es()


@shared_task(bind=True)
def remove_service_checks(self, service_id):
    """
    Remove all checks from a service.
    """
    from hypermap.aggregator.models import Service
    service = Service.objects.get(id=service_id)

    service.check_set.all().delete()
    layer_to_process = service.layer_set.all()
    for layer in layer_to_process:
        layer.check_set.all().delete()


@shared_task(bind=True)
def index_service(self, service_id):
    """
    Index a service in search engine.
    """

    from hypermap.aggregator.models import Service
    service = Service.objects.get(id=service_id)

    if not service.is_valid:
        LOGGER.debug('Not indexing service with id %s in search engine as it is not valid' % service.id)
        return

    LOGGER.debug('Indexing service %s' % service.id)
    layer_to_process = service.layer_set.all()

    for layer in layer_to_process:
        if not settings.REGISTRY_SKIP_CELERY:
            index_layer(layer.id, use_cache=True)
        else:
            index_layer(layer.id)


@shared_task(bind=True)
def index_layer(self, layer_id, use_cache=False):
    """Index a layer in the search backend.
    If cache is set, append it to the list, if it isn't send the transaction right away.
    cache needs memcached to be available.
    """

    from hypermap.aggregator.models import Layer
    layer = Layer.objects.get(id=layer_id)

    if not layer.is_valid:
        LOGGER.debug('Not indexing or removing layer with id %s in search engine as it is not valid' % layer.id)
        unindex_layer(layer.id, use_cache)
        return

    if layer.was_deleted:
        LOGGER.debug('Not indexing or removing layer with id %s in search engine as was_deleted is true' % layer.id)
        unindex_layer(layer.id, use_cache)
        return

    # 1. if we use cache
    if use_cache:
        LOGGER.debug('Caching layer with id %s for syncing with search engine' % layer.id)
        layers = cache.get('layers')
        if layers is None:
            layers = set([layer.id])
        else:
            layers.add(layer.id)
        cache.set('layers', layers)
        return

    # 2. if we don't use cache
    # TODO: Make this function more DRY
    # by abstracting the common bits.
    if SEARCH_TYPE == 'solr':
        from hypermap.aggregator.solr import SolrHypermap
        LOGGER.debug('Syncing layer %s to solr' % layer.name)
        solrobject = SolrHypermap()
        success, message = solrobject.layer_to_solr(layer)
        # update the error message if using celery
        if not settings.REGISTRY_SKIP_CELERY:
            if not success:
                self.update_state(
                    state=states.FAILURE,
                    meta=message
                    )
                raise Ignore()
    elif SEARCH_TYPE == 'elasticsearch':
        from hypermap.aggregator.elasticsearch_client import ESHypermap
        LOGGER.debug('Syncing layer %s to es' % layer.name)
        esobject = ESHypermap()
        success, message = esobject.layer_to_es(layer)
        # update the error message if using celery
        if not settings.REGISTRY_SKIP_CELERY:
            if not success:
                self.update_state(
                    state=states.FAILURE,
                    meta=message
                    )
                raise Ignore()


@shared_task(bind=True)
def unindex_layer(self, layer_id, use_cache=False):
    """
    Remove the index for a layer in the search backend.
    If cache is set, append it to the list of removed layers, if it isn't send the transaction right away.
    """

    from hypermap.aggregator.models import Layer
    layer = Layer.objects.get(id=layer_id)

    if use_cache:
        LOGGER.debug('Caching layer with id %s for being removed from search engine' % layer.id)
        deleted_layers = cache.get('deleted_layers')
        if deleted_layers is None:
            deleted_layers = set([layer.id])
        else:
            deleted_layers.add(layer.id)
        cache.set('deleted_layers', deleted_layers)
        return

    if SEARCH_TYPE == 'solr':
        from hypermap.aggregator.solr import SolrHypermap
        LOGGER.debug('Removing layer %s from solr' % layer.id)
        try:
            solrobject = SolrHypermap()
            solrobject.remove_layer(layer.uuid)
        except Exception:
            LOGGER.error('Layer NOT correctly removed from Solr')
    elif SEARCH_TYPE == 'elasticsearch':
        # TODO implement me
        pass


@shared_task(bind=True)
def index_all_layers(self):
    """
    Index all layers in search engine.
    """
    from hypermap.aggregator.models import Layer

    if not settings.REGISTRY_SKIP_CELERY:
        layers_cache = set(Layer.objects.filter(is_valid=True).values_list('id', flat=True))
        deleted_layers_cache = set(Layer.objects.filter(is_valid=False).values_list('id', flat=True))
        cache.set('layers', layers_cache)
        cache.set('deleted_layers', deleted_layers_cache)
    else:
        for layer in Layer.objects.all():
            index_layer(layer.id)


@shared_task(bind=True)
def update_last_wm_layers(self, num_layers=10):
    """
    Update and index the last added and deleted layers (num_layers) in WorldMap service.
    """
    from hypermap.aggregator.models import Service
    from hypermap.aggregator.models import update_layers_wm

    LOGGER.debug(
        'Updating the index the last %s added and %s deleted layers in WorldMap service'
        % (num_layers, num_layers)
                )
    service = Service.objects.filter(type='Hypermap:WorldMap')[0]
    update_layers_wm(service, num_layers)

    # Remove in search engine last num_layers that were deleted
    LOGGER.debug('Removing the index for the last %s deleted layers' % num_layers)
    layer_to_unindex = service.layer_set.filter(was_deleted=True).order_by('-last_updated')[0:num_layers]
    for layer in layer_to_unindex:
        if not settings.REGISTRY_SKIP_CELERY:
            unindex_layer(layer.id, use_cache=True)
        else:
            unindex_layer(layer.id)

    # Add/Update in search engine last num_layers that were added
    LOGGER.debug('Adding/Updating the index for the last %s added layers' % num_layers)
    layer_to_index = service.layer_set.filter(was_deleted=False).order_by('-last_updated')[0:num_layers]
    for layer in layer_to_index:
        if not settings.REGISTRY_SKIP_CELERY:
            index_layer(layer.id, use_cache=True)
        else:
            index_layer(layer.id)


@shared_task(bind=True)
def update_endpoint(self, endpoint_id, greedy_opt=False):
    from hypermap.aggregator.utils import create_services_from_endpoint
    from hypermap.aggregator.models import Endpoint

    endpoint = Endpoint.objects.get(id=endpoint_id)

    LOGGER.debug('Processing endpoint with id %s: %s' % (endpoint.id, endpoint.url))

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
def update_endpoints(self, endpoint_list_id):
    from hypermap.aggregator.models import EndpointList
    endpoint_list_to_process = EndpointList.objects.get(id=endpoint_list_id)
    # for now we process the enpoint even if they were already processed
    endpoint_to_process = endpoint_list_to_process.endpoint_set.filter(processed=False)
    if not settings.REGISTRY_SKIP_CELERY:
        for endpoint in endpoint_to_process:
            update_endpoint.delay(endpoint.id)
    else:
        for endpoint in endpoint_to_process:
            update_endpoint(endpoint.id)
    return True
