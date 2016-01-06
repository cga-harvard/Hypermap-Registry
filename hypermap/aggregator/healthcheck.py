import datetime

from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService

from models import Status

def check_service(service):
    """
    Tests a service and provide run metrics.
    """
    if service.type == 'OGC:WMS':
        ows = WebMapService(service.url)
    if service.type == 'OGC:WMTS':
        ows = WebMapTileService(service.url)
    # TODO add more service types here

    success = True
    start_time = datetime.datetime.utcnow()
    message = ''

    try:
        if service.type.startswith('OGC:'):
            title = ows.identification.title
        if title is None:
            title = '%s %s' % (resource_type, service.url)

        # update title
        service.title = title
        service.save()

    except Exception, err:
        message = str(err)
        success = False

    end_time = datetime.datetime.utcnow()

    delta = end_time - start_time
    response_time = '%s.%s' % (delta.seconds, delta.microseconds)

    status = Status(
        resource = service,
        success = success,
        response_time = response_time,
        message = message
    )
    status.save()
