from .models import Service
from .enums import SUPPORTED_SRS


def report_services(services):

    total_supported_services = 0
    total_services = services.count()
    total_layers = 0
    total_supported_layers = 0

    for service in services:
        total_layers = total_layers + service.layer_set.all().count()
        service_srs_list = service.srs.values_list('code',flat=True)
        for srs in service_srs_list:
            if srs in SUPPORTED_SRS:
                total_supported_services = total_supported_services + 1
                total_supported_layers = total_supported_layers + service.layer_set.all().count()
                break

    return total_supported_layers, total_layers, total_supported_services, total_services


services = Service.objects.filter(type__in=['ESRI:ArcGIS:MapServer', 'ESRI:ArcGIS:ImageServer', ])
print 'ESRI: total_supported_layers: %s, total_layers %s, total_supported_services %s, total_services %s' % report_services(services)

services = Service.objects.filter(type__in=['OGC:WMS', 'Hypermap:WorldMap', 'Hypermap:WARPER', ])
print 'OGC: total_supported_layers: %s, total_layers %s, total_supported_services %s, total_services %s' % report_services(services)
