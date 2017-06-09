import urllib2
import logging

from django.conf import settings
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from djmp.views import get_mapproxy


from models import Service, Layer, Catalog
from tasks import (check_all_services, check_service, check_layer, remove_service_checks,
                   index_service, index_all_layers, index_layer, index_cached_layers, clear_index,
                   SEARCH_TYPE, SEARCH_URL)
from enums import SERVICE_TYPES


LOGGER = logging.getLogger(__name__)


class BootstrapPaginator(Paginator):
    def __init__(self, *args, **kwargs):
        """
        :param wing_pages: How many pages will be shown before and after current page.
        """
        self.wing_pages = kwargs.pop('wing_pages', 3)
        super(BootstrapPaginator, self).__init__(*args, **kwargs)

    def _get_page(self, *args, **kwargs):
        self.page = super(BootstrapPaginator, self)._get_page(*args, **kwargs)
        return self.page

    @property
    def page_range(self):
        return range(max(self.page.number - self.wing_pages, 1),
                     min(self.page.number + self.wing_pages + 1, self.num_pages + 1))


def serialize_checks(check_set):
    """
    Serialize a check_set for raphael
    """
    check_set_list = []
    for check in check_set.all()[:25]:
        check_set_list.append(
            {
                'datetime': check.checked_datetime.isoformat(),
                'value': check.response_time,
                'success': 1 if check.success else 0
            }
        )
    return check_set_list


@login_required
def domains(request):
    """
    A page with number of services and layers faceted on domains.
    """
    url = ''
    query = '*:*&facet=true&facet.limit=-1&facet.pivot=domain_name,service_id&wt=json&indent=true&rows=0'
    if settings.SEARCH_TYPE == 'elasticsearch':
        url = '%s/select?q=%s' % (settings.SEARCH_URL, query)
    if settings.SEARCH_TYPE == 'solr':
        url = '%s/solr/hypermap/select?q=%s' % (settings.SEARCH_URL, query)
    LOGGER.debug(url)
    response = urllib2.urlopen(url)
    data = response.read().replace('\n', '')
    # stats
    layers_count = Layer.objects.all().count()
    services_count = Service.objects.all().count()
    template = loader.get_template('aggregator/index.html')
    context = RequestContext(request, {
        'data': data,
        'layers_count': layers_count,
        'services_count': services_count,
    })
    return HttpResponse(template.render(context))


def index(request, catalog_slug=None):
    order_by = request.GET.get('order_by', '-last_updated')
    filter_by = request.GET.get('filter_by', None)
    query = request.GET.get('q', None)

    services = Service.objects.all()
    if catalog_slug:
        services = Service.objects.filter(catalog__slug=catalog_slug)

    # order_by
    if 'total_checks' in order_by:
        services = services.annotate(total_checks=Count('resource_ptr__check')).order_by(order_by)
    elif 'layers_count' in order_by:
        services = services.annotate(layers_count=Count('layer')).order_by(order_by)
    else:
        services = services.order_by(order_by)
    # filter_by
    if filter_by:
        services = services.filter(type__exact=filter_by)
    # query
    if query:
        services = services.filter(url__icontains=query)
    # types filter
    types_list = []
    for service_type in SERVICE_TYPES:
        type_item = []
        service_type_code = service_type[0]
        type_item.append(service_type_code)
        type_item.append(service_type[1])
        type_item.append(Service.objects.filter(type__exact=service_type_code).count())
        types_list.append(type_item)

    page = request.GET.get('page', 1)
    services = services.only('id',)
    paginator = BootstrapPaginator(services, 10)

    try:
        services = paginator.page(page)
    except PageNotAnInteger:
        services = paginator.page(1)
    except EmptyPage:
        services = paginator.page(paginator.num_pages)

    # stats
    layers_count = Layer.objects.all().count()
    services_count = Service.objects.all().count()

    template = loader.get_template('aggregator/search.html')
    context = RequestContext(request, {
        'services': services,
        'types_list': types_list,
        'layers_count': layers_count,
        'services_count': services_count,
        'catalogs': Catalog.objects.filter(url__isnull=False)
    })
    return HttpResponse(template.render(context))


def service_detail(request, catalog_slug, service_uuid=None, service_id=None):

    if service_uuid is not None:
        service = get_object_or_404(Service, uuid=service_uuid)
    else:
        service = get_object_or_404(Service, pk=service_id)

    if request.method == 'POST':
        if 'check' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                check_service(service.id)
            else:
                check_service.delay(service.id)
        if 'remove' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                remove_service_checks(service.id)
            else:
                remove_service_checks.delay(service.id)
        if 'index' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                index_service(service.id)
            else:
                index_service.delay(service.id)

    page = request.GET.get('page', 1)
    layers = service.layer_set.all().only('id',)
    paginator = BootstrapPaginator(layers, 10)

    try:
        layers = paginator.page(page)
    except PageNotAnInteger:
        layers = paginator.page(1)
    except EmptyPage:
        layers = paginator.page(paginator.num_pages)

    return render(request, 'aggregator/service_detail.html', {'service': service,
                                                              'layers': layers,
                                                              'SEARCH_TYPE': SEARCH_TYPE,
                                                              'SEARCH_URL': SEARCH_URL.rstrip('/'),
                                                              'catalog_slug': catalog_slug})


def service_checks(request, catalog_slug, service_uuid):
    service = get_object_or_404(Service, uuid=service_uuid)
    resource = serialize_checks(service.check_set)

    page = request.GET.get('page', 1)
    checks = service.check_set.all()
    paginator = BootstrapPaginator(checks, 10)

    try:
        checks = paginator.page(page)
    except PageNotAnInteger:
        checks = paginator.page(1)
    except EmptyPage:
        checks = paginator.page(paginator.num_pages)

    return render(request, 'aggregator/service_checks.html', {'service': service,
                                                              'checks': checks,
                                                              'resource': resource})


def layer_detail(request, catalog_slug, layer_uuid=None, layer_id=None):
    if layer_uuid is not None:
        layer = get_object_or_404(Layer, uuid=layer_uuid)
    else:
        layer = get_object_or_404(Layer, pk=layer_id)

    if request.method == 'POST':
        if 'check' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                check_layer(layer.id)
            else:
                check_layer.delay(layer.id)
        if 'remove' in request.POST:
            layer.check_set.all().delete()
        if 'index' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                index_layer(layer.id)
            else:
                index_layer.delay(layer.id)

    return render(request, 'aggregator/layer_detail.html', {'layer': layer,
                                                            'SEARCH_TYPE': SEARCH_TYPE,
                                                            'SEARCH_URL': SEARCH_URL.rstrip('/'),
                                                            'catalog_slug': catalog_slug})


def layer_checks(request, catalog_slug, layer_uuid):
    layer = get_object_or_404(Layer, uuid=layer_uuid)
    resource = serialize_checks(layer.check_set)

    page = request.GET.get('page', 1)
    checks = layer.check_set.all()
    paginator = BootstrapPaginator(checks, 10)

    try:
        checks = paginator.page(page)
    except PageNotAnInteger:
        checks = paginator.page(1)
    except EmptyPage:
        checks = paginator.page(paginator.num_pages)

    return render(request, 'aggregator/layer_checks.html', {'layer': layer,
                                                            'checks': checks,
                                                            'resource': resource})


@login_required
def tasks_runner(request):
    """
    A page that let the admin to run global tasks.
    """

    # server info
    cached_layers_number = 0
    cached_layers = cache.get('layers')
    if cached_layers:
        cached_layers_number = len(cached_layers)

    cached_deleted_layers_number = 0
    cached_deleted_layers = cache.get('deleted_layers')
    if cached_deleted_layers:
        cached_deleted_layers_number = len(cached_deleted_layers)

    # task actions
    if request.method == 'POST':
        if 'check_all' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                check_all_services()
            else:
                check_all_services.delay()
        if 'index_all' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                index_all_layers()
            else:
                index_all_layers.delay()
        if 'index_cached' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                index_cached_layers()
            else:
                index_cached_layers.delay()
        if 'drop_cached' in request.POST:
            cache.set('layers', None)
            cache.set('deleted_layers', None)
        if 'clear_index' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                clear_index()
            else:
                clear_index.delay()

    return render(
        request,
        'aggregator/tasks_runner.html', {
            'cached_layers_number': cached_layers_number,
            'cached_deleted_layers_number': cached_deleted_layers_number,
        }
    )


def layer_mapproxy(request, catalog_slug, layer_uuid, path_info):
    # Get Layer with matching catalog and uuid
    layer = get_object_or_404(Layer,
                              uuid=layer_uuid,
                              catalog__slug=catalog_slug)

    # for WorldMap layers we need to use the url of the layer
    if layer.service.type == 'Hypermap:WorldMap':
        layer.service.url = layer.url

    # Set up a mapproxy app for this particular layer
    mp, yaml_config = get_mapproxy(layer)

    query = request.META['QUERY_STRING']

    if len(query) > 0:
        path_info = path_info + '?' + query

    params = {}
    headers = {
            'X-Script-Name': '/registry/{0}/layer/{1}/map/'.format(catalog_slug, layer.id),
            'X-Forwarded-Host': request.META['HTTP_HOST'],
            'HTTP_HOST': request.META['HTTP_HOST'],
            'SERVER_NAME': request.META['SERVER_NAME'],
            }

    if path_info == '/config':
        response = HttpResponse(yaml_config, content_type='text/plain')
        return response

    # Get a response from MapProxy as if it was running standalone.
    mp_response = mp.get(path_info, params, headers)

    # Create a Django response from the MapProxy WSGI response.
    response = HttpResponse(mp_response.body, status=mp_response.status_int)
    for header, value in mp_response.headers.iteritems():
        response[header] = value

    return response
