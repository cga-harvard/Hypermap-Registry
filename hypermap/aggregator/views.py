from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render
from django.shortcuts import get_object_or_404

from models import Service, Layer


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


def index(request):
    # services = Service.objects.annotate(
    #    num_checks=Count('resource_ptr__check')).filter(num_checks__gt=0)
    # services = Service.objects.filter(check__isnull=False)
    services = Service.objects.all()
    layers_count = Layer.objects.all().count()
    template = loader.get_template('aggregator/index.html')
    context = RequestContext(request, {
        'services': services,
        'layers_count': layers_count,
    })
    return HttpResponse(template.render(context))


def service_detail(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    resource = serialize_checks(service.check_set)
    return render(request, 'aggregator/service_detail.html', {'service': service, 'resource': resource})


def layer_detail(request, layer_id):
    layer = get_object_or_404(Layer, pk=layer_id)
    resource = serialize_checks(layer.check_set)
    return render(request, 'aggregator/layer_detail.html', {'layer': layer, 'resource': resource})
