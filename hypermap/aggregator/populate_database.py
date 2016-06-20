from django.conf import settings

from models import Service
from utils import create_services_from_endpoint


def populate_initial_services():
    """
    Populate a fresh installed Hypermap instances with basic services.
    """
    services_list = (
        (
            'Harvard WorldMap',
            'Harvard WorldMap open source web geospatial platform',
            'Hypermap:WorldMap',
            'http://worldmap.harvard.edu'
        ),
        (
            'NYPL MapWarper',
            'The New York Public Library (NYPL) MapWarper web site',
            'Hypermap:WARPER',
            'http://maps.nypl.org/warper/maps'
        ),
        (
            'Map Warper',
            'The MapWarper web site developed, hosted and maintained by Tim Waters',
            'Hypermap:WARPER',
            'http://mapwarper.net/maps'
        ),
        (
            'WorldMap Warp',
            'The MapWarper instance part of the Harvard WorldMap project',
            'Hypermap:WARPER',
            'http://warp.worldmap.harvard.edu/maps'
        ),
        (
            'WFP GeoNode',
            'World Food Programme GeoNode',
            'OGC:WMS',
            'http://geonode.wfp.org/geoserver/ows?'
        ),
        (
            'NASA EARTHDATA',
            'NASA EARTHDATA, powered by EOSDIS',
            'OGC:WMTS',
            'http://map1.vis.earthdata.nasa.gov/wmts-geo/1.0.0/WMTSCapabilities.xml'
        ),
    )

    esri_endpoint = 'https://gis.ngdc.noaa.gov/arcgis/rest/services'
    print '*** Importing esri endpoint: %s' % esri_endpoint
    create_services_from_endpoint(esri_endpoint)

    for service in services_list:
        print '*** Importing %s' % service[0]
        service = Service(
            title=service[0],
            abstract=service[1],
            type=service[2],
            url=service[3]
        )
        service.save()

settings.SKIP_CELERY_TASK = True
populate_initial_services()
