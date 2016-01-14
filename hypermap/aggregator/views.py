from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render
from django.shortcuts import get_object_or_404

from models import Service, Layer


def index(request):
    services = Service.objects.all()
    template = loader.get_template('aggregator/index.html')
    context = RequestContext(request, {
        'services': services,
    })
    return HttpResponse(template.render(context))


def service_detail(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    return render(request, 'aggregator/service_detail.html', {'service': service})


def layer_detail(request, layer_id):
    layer = get_object_or_404(Layer, pk=layer_id)
    return render(request, 'aggregator/layer_detail.html', {'layer': layer})
