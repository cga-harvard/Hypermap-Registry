from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count

from models import Service, Layer


def index(request):
    #services = Service.objects.all()
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
    return render(request, 'aggregator/service_detail.html', {'service': service})


def layer_detail(request, layer_id):
    layer = get_object_or_404(Layer, pk=layer_id)
    return render(request, 'aggregator/layer_detail.html', {'layer': layer})
