import datetime

from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService

from models import Check, Layer, SpatialReferenceSystem

def check_service(service):
    """
    Tests a service and provide run metrics.
    """
    if service.type == 'OGC:WMS':
        ows = WebMapService(service.url)
        check_wms_layers(service)
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

    check = Check(
        resource = service,
        success = success,
        response_time = response_time,
        message = message
    )
    check.save()


def check_wms_layers(service):
    """
    Tests a WMS service and provide run metrics.
    """
    wms = WebMapService(service.url)
    layer_names = list(wms.contents)
    for layer_name in layer_names:
        ows_layer = wms.contents[layer_name]
        print ows_layer.name
        # get or create layer
        layer, created = Layer.objects.get_or_create(name=ows_layer.name, owner=service.owner, service=service)
        # update fields
        layer.title = ows_layer.title
        layer.abstract = ows_layer.abstract
        # bbox
        bbox = list(ows_layer.boundingBoxWGS84 or (-179.0, -89.0, 179.0, 89.0))
        layer.bbox_x0 = bbox[0]
        layer.bbox_y0 = bbox[1]
        layer.bbox_x1 = bbox[2]
        layer.bbox_y1 = bbox[3]
        # crsOptions
        # TODO we may rather prepopulate with fixutres the SpatialReferenceSystem table
        for crs_code in ows_layer.crsOptions:
            srs, created = SpatialReferenceSystem.objects.get_or_create(code=crs_code)
        layer.srs.add(srs)
        layer.save()
        # now the metrics
        success = True
        start_time = datetime.datetime.utcnow()
        message = ''

        try:
            # get map here
            #import ipdb;ipdb.set_trace()
            img = wms.getmap(layers=[layer.name],
                                srs='EPSG:4326',
                                bbox=(layer.bbox_x0, layer.bbox_y0, layer.bbox_x1, layer.bbox_y1),
                                size=(50, 50),
                                format='image/jpeg',
                                transparent=True
                            )

            from django.core.files.uploadedfile import SimpleUploadedFile
            thumbnail_file_name = '%s.jpg' % layer.name
            upfile = SimpleUploadedFile(thumbnail_file_name, img.read(), "image/jpeg")
            layer.thumbnail.save(thumbnail_file_name, upfile, True)

            print 'GetMap done'

        except Exception, err:
            message = str(err)
            success = False

        end_time = datetime.datetime.utcnow()

        delta = end_time - start_time
        response_time = '%s.%s' % (delta.seconds, delta.microseconds)

        check = Check(
            resource = layer,
            success = success,
            response_time = response_time,
            message = message
        )
        check.save()
