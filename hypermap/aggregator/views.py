from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count

from models import Service, Layer


def index(request):
    services = Service.objects.annotate(
        num_checks=Count('resource_ptr__check')).filter(num_checks__gt=0)
    layers_count = Layer.objects.annotate(
        num_checks=Count('resource_ptr__check')).filter(num_checks__gt=0).count()
    template = loader.get_template('aggregator/index.html')
    context = RequestContext(request, {
        'services': services,
        'layers_count': layers_count,
    })
    return HttpResponse(template.render(context))


def service_detail(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    check_set = []
    for check in service.check_set.all():
        check_set.append({'datetime': check.checked_datetime.isoformat(),
                         'value': check.response_time,
                          'success': 1 if check.success else 0})
    return render(request, 'aggregator/service_detail.html', {'service': service, 'resource': check_set})


def layer_detail(request, layer_id):
    layer = get_object_or_404(Layer, pk=layer_id)
    check_set = []
    for check in layer.check_set.all():
        check_set.append({'datetime': check.checked_datetime.isoformat(),
                         'value': check.response_time,
                          'success': 1 if check.success else 0})
    return render(request, 'aggregator/layer_detail.html', {'layer': layer, 'resource': check_set})
