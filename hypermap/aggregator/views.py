import urllib2
import json
import pika

from django.conf import settings
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from djmp.views import get_mapproxy


from models import Service, Layer, Catalog
from tasks import (check_all_services, check_service, check_layer, remove_service_checks,
                   index_service, index_all_layers, index_layer, clear_index,
                   SEARCH_TYPE, SEARCH_URL)
from enums import SERVICE_TYPES

from hypermap import celeryapp


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
    url = ('%s/select?q=*:*&facet=true&facet.limit=-1&facet.pivot=domain_name,service_id&wt=json&indent=true&rows=0'
           % SEARCH_URL)
    print url
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


def service_detail(request, catalog_slug, service_id):
    service = get_object_or_404(Service,
                                pk=service_id,
                                catalog__slug=catalog_slug)

    if request.method == 'POST':
        if 'check' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                check_service(service)
            else:
                check_service.delay(service)
        if 'remove' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                remove_service_checks(service)
            else:
                remove_service_checks.delay(service)
        if 'index' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                index_service(service)
            else:
                index_service.delay(service)

    return render(request, 'aggregator/service_detail.html', {'service': service,
                                                              'SEARCH_TYPE': SEARCH_TYPE,
                                                              'SEARCH_URL': SEARCH_URL.rstrip('/'),
                                                              'catalog_slug': catalog_slug})


def service_checks(request, catalog_slug, service_id):
    service = get_object_or_404(Service,
                                pk=service_id,
                                catalog__slug=catalog_slug)
    resource = serialize_checks(service.check_set)

    return render(request, 'aggregator/service_checks.html', {'service': service, 'resource': resource})


def layer_detail(request, catalog_slug, layer_id):
    layer = get_object_or_404(Layer,
                              pk=layer_id,
                              catalog__slug=catalog_slug)

    if request.method == 'POST':
        if 'check' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                check_layer(layer)
            else:
                check_layer.delay(layer)
        if 'remove' in request.POST:
            layer.check_set.all().delete()
        if 'index' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                index_layer(layer)
            else:
                index_layer.delay(layer)

    return render(request, 'aggregator/layer_detail.html', {'layer': layer,
                                                            'SEARCH_TYPE': SEARCH_TYPE,
                                                            'SEARCH_URL': SEARCH_URL.rstrip('/'),
                                                            'catalog_slug': catalog_slug})


def layer_checks(request, catalog_slug, layer_id):
    layer = get_object_or_404(Layer,
                              pk=layer_id,
                              catalog__slug=catalog_slug)
    resource = serialize_checks(layer.check_set)

    return render(request, 'aggregator/layer_checks.html', {'layer': layer, 'resource': resource})


@login_required
def celery_monitor(request):
    """
    A raw celery monitor to figure out which processes are active and reserved.
    """
    inspect = celeryapp.app.control.inspect()
    active_json = inspect.active()
    reserved_json = inspect.reserved()
    active_tasks = []
    if active_json:
        for worker in active_json.keys():
            for task in active_json[worker]:
                id = task['id']
                # not sure why these 2 fields are not already in AsyncResult
                name = task['name']
                time_start = task['time_start']
                args = task['args']
                active_task = celeryapp.app.AsyncResult(id)
                active_task.name = name
                active_task.args = args
                active_task.worker = '%s, pid: %s' % (worker, task['worker_pid'])
                active_task.time_start = time_start
                task_id_sanitized = id.replace('-', '_')
                active_task.task_id_sanitized = task_id_sanitized
                active_tasks.append(active_task)
    reserved_tasks = []
    if reserved_json:
        for worker in active_json.keys():
            for task in reserved_json[worker]:
                id = task['id']
                name = task['name']
                args = task['args']
                reserved_task = celeryapp.app.AsyncResult(id)
                reserved_task.name = name
                reserved_task.args = args
                reserved_tasks.append(reserved_task)

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
        if 'clear_index' in request.POST:
            if settings.REGISTRY_SKIP_CELERY:
                clear_index()
            else:
                clear_index.delay()
    return render(
        request,
        'aggregator/celery_monitor.html',
        {
            'active_tasks': active_tasks,
            'reserved_tasks': reserved_tasks,
            'jobs': get_queued_jobs_number(),
        }
    )


def get_queued_jobs_number():
    # to detect tasks in the queued the only way is to use amqplib so far
    from amqplib import client_0_8 as amqp

    params = pika.URLParameters(settings.BROKER_URL)

    conn = amqp.Connection(host='{0}:{1}'.format(params.host, params.port),
                           userid=params.credentials.username,
                           password=params.credentials.password,
                           virtual_host=params.virtual_host,
                           insist=False)
    chan = conn.channel()
    name, jobs, consumers = chan.queue_declare(queue="hypermap", passive=False)
    return jobs


@login_required
def update_jobs_number(request):
    response_data = {}
    response_data['jobs'] = get_queued_jobs_number()
    json_data = json.dumps(response_data)
    return HttpResponse(json_data, content_type="application/json")


@login_required
def update_progressbar(request, task_id):
    response_data = {}
    active_task = celeryapp.app.AsyncResult(task_id)
    progressbar = 100
    status = '100%'
    state = 'COMPLETED'
    if active_task:
        if not active_task.ready():
            current = active_task.info['current']
            total = active_task.info['total']
            progressbar = (current / float(total) * 100)
            status = "%s/%s (%.2f %%)" % (current, total, progressbar)
            state = active_task.state
    response_data['progressbar'] = progressbar
    response_data['status'] = status
    response_data['state'] = state
    json_data = json.dumps(response_data)
    return HttpResponse(json_data, content_type="application/json")


def layer_mapproxy(request, catalog_slug, layer_id, path_info):
    # Get Layer with matching catalog and primary key
    layer = get_object_or_404(Layer,
                              pk=layer_id,
                              catalog__slug=catalog_slug)

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
