import datetime
import os
import re
import urllib2
from urlparse import urlparse
from dateutil.parser import parse

from django.conf import settings
from django.db import models
from django.db.models import Avg, Min, Max
from django.db.models import signals
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django_extensions.db.fields import AutoSlugField

from taggit.managers import TaggableManager
from polymorphic.models import PolymorphicModel
from lxml import etree
from shapely.wkt import loads
from owslib.namespaces import Namespaces
from owslib.util import nspath_eval
from owslib.tms import TileMapService
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
from arcrest import MapService as ArcMapService, ImageService as ArcImageService

from enums import SERVICE_TYPES, DATE_TYPES
from tasks import update_endpoints, check_service, check_layer, index_layer
#from utils import bbox2wktpolygon


def get_parsed_date(sdate):
    try:
        pydate = parse(sdate, yearfirst=True)
        # parser has a problem for dates from 1 to 100
        if sdate[:2] == '00' or sdate[:3] == '000':
            effective_year = int(sdate[:4])
            effective_pydate = datetime.datetime(effective_year, pydate.month, pydate.day)
            pydate = effective_pydate
        return pydate
    except:
        return None


class Resource(PolymorphicModel):
    """
    Resource represents basic information for a resource (service/layer).
    """
    type = models.CharField(max_length=32, choices=SERVICE_TYPES)
    title = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    keywords = TaggableManager(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    url = models.URLField(max_length=255)
    is_public = models.BooleanField(default=True)

    temporal_extent_start = models.CharField(max_length=255, null=True, blank=True)
    temporal_extent_end = models.CharField(max_length=255, null=True, blank=True)

    # CSW fields
    csw_type = models.CharField(max_length=32, default='dataset', null=False)
    csw_typename = models.CharField(max_length=32, default='csw:Record', null=False)

    csw_schema = models.CharField(max_length=64,
                                  default='http://www.opengis.net/cat/csw/2.0.2',
                                  null=False)

    anytext = models.TextField(null=True, blank=True)
    wkt_geometry = models.TextField(null=False,
                                    default='POLYGON((-180 -90,-180 90,180 90,180 -90,-180 -90))')

    # metadata XML specific fields
    xml = models.TextField(null=True,
                           default='<csw:Record xmlns:csw="http://www.opengis.net/cat/2.0.2"/>',
                           blank=True)

    def __unicode__(self):
        return '%s - %s' % (self.polymorphic_ctype.name, self.id)

    @property
    def id_string(self):
        return str(self.id)

    @property
    def last_updated_iso8601(self):
        if self.last_updated:
            iso8601 = self.last_updated.isoformat()
            if not self.last_updated.utcoffset:
                return '%sZ' % iso8601
            return iso8601

    @property
    def keywords_csv(self):
        keywords_qs = self.keywords.all()
        if keywords_qs:
            return ','.join([kw.name for kw in keywords_qs])
        else:
            return ''

    @property
    def first_check(self):
        return self.check_set.order_by('checked_datetime')[0].checked_datetime

    @property
    def last_check(self):
        if self.check_set.all().count() > 0:
            return self.check_set.order_by('-checked_datetime')[0].checked_datetime
        else:
            return None

    @property
    def average_response_time(self):
        return self.check_set.aggregate(Avg('response_time')).values()[0]

    @property
    def min_response_time(self):
        return self.check_set.aggregate(Min('response_time')).values()[0]

    @property
    def max_response_time(self):
        return self.check_set.aggregate(Max('response_time')).values()[0]

    @property
    def last_response_time(self):
        if self.checks_count > 0:
            return self.check_set.order_by('-checked_datetime')[0].response_time
        else:
            return None

    @property
    def last_status(self):
        if self.checks_count > 0:
            return self.check_set.order_by('-checked_datetime')[0].success
        else:
            return None

    @property
    def checks_count(self):
        return self.check_set.all().count()

    @property
    def reliability(self):
        total_checks = self.check_set.count()
        if total_checks:
            success_checks = self.check_set.filter(success=True).count()
            return (success_checks/float(total_checks)) * 100
        else:
            return None

    @property
    def recent_reliability(self):
        total_checks = self.check_set.count()
        recent_checks_number = 2
        if total_checks >= recent_checks_number:
            recent_checks = self.check_set.all().order_by('-checked_datetime')[0:recent_checks_number]
            success_checks = sum(check.success for check in recent_checks)
            return (success_checks/float(recent_checks_number)) * 100
        else:
            return self.reliability


class Service(Resource):
    """
    Service represents a remote geowebservice.
    """

    def __unicode__(self):
        return '%s - %s' % (self.id, self.title)

    @property
    def get_domain(self):
        parsed_uri = urlparse(self.url)
        domain = '{uri.netloc}'.format(uri=parsed_uri)
        return domain

    def update_layers(self):
        """
        Update layers for a service.
        """
        from utils import (update_layers_wms, update_layers_wmts, update_layers_esri_mapserver,
                           update_layers_esri_imageserver, update_layers_wm, update_layers_warper)
        signals.post_save.disconnect(layer_post_save, sender=Layer)
        print 'Updating layers for service id %s' % self.id
        if self.type == 'OGC:WMS':
            update_layers_wms(self)
        elif self.type == 'OGC:WMTS':
            update_layers_wmts(self)
        elif self.type == 'ESRI:ArcGIS:MapServer':
            update_layers_esri_mapserver(self)
        elif self.type == 'ESRI:ArcGIS:ImageServer':
            update_layers_esri_imageserver(self)
        elif self.type == 'WM':
            update_layers_wm(self)
        elif self.type == 'WARPER':
            update_layers_warper(self)
        signals.post_save.connect(layer_post_save, sender=Layer)

    def check_available(self):
        """
        Check for availability of a service and provide run metrics.
        """
        from utils import get_esri_service_name
        success = True
        start_time = datetime.datetime.utcnow()
        message = ''

        print 'Checking service id %s' % self.id

        try:
            title = None
            abstract = None
            keywords = []
            wkt_geometry = None
            srs = '4326'
            if self.type == 'OGC:WMS':
                ows = WebMapService(self.url)
                title = ows.identification.title
                abstract = ows.identification.abstract
                keywords = ows.identification.keywords
                for c in ows.contents:
                    if ows.contents[c].parent is None:
                        wkt_geometry = bbox2wktpolygon(ows.contents[c].boundingBoxWGS84)
                    break
            if self.type == 'OGC:WMTS':
                ows = WebMapTileService(self.url)
                title = ows.identification.title
                abstract = ows.identification.abstract
                keywords = ows.identification.keywords
            if self.type == 'OGC:TMS':
                ows = TileMapService(self.url)
                title = ows.identification.title
                abstract = ows.identification.abstract
                keywords = ows.identification.keywords
            if self.type == 'ESRI:ArcGIS:MapServer':
                esri = ArcMapService(self.url)
                title = esri.mapName
                if len(title) == 0:
                    title = get_esri_service_name(self.url)
                srs = esri.fullExtent.spatialReference.wkid
                wkt_geometry = bbox2wktpolygon([esri.fullExtent.xmin,
                                                esri.fullExtent.ymin,
                                                esri.fullExtent.xmax,
                                                esri.fullExtent.ymax
                                               ])
            if self.type == 'ESRI:ArcGIS:ImageServer':
                esri = ArcImageService(self.url)
                title = esri._json_struct['name']
                if len(title) == 0:
                    title = get_esri_service_name(self.url)
                srs = esri.fullExtent.spatialReference.wkid
                wkt_geometry = bbox2wktpolygon([esri.fullExtent.xmin,
                                                esri.fullExtent.ymin,
                                                esri.fullExtent.xmax,
                                                esri.fullExtent.ymax
                                               ])
            if self.type == 'WM':
                urllib2.urlopen(self.url)
                title = 'Harvard WorldMap'
            if self.type == 'WARPER':
                urllib2.urlopen(self.url)
            # update title without raising a signal and recursion
            if title:
                self.title = title
                Service.objects.filter(id=self.id).update(title=title)
            if abstract:
                self.abstract = abstract
                Service.objects.filter(id=self.id).update(abstract=abstract)
            if keywords:
                for kw in keywords:
                    # FIXME: persist keywords to Django model
                    self.keywords.add(kw)
            if wkt_geometry:
                self.wkt_geometry = wkt_geometry
                Service.objects.filter(id=self.id).update(wkt_geometry=wkt_geometry)
            xml = create_metadata_record(
                identifier=self.id_string,
                source=self.url,
                links=[[self.type, self.url]],
                format=self.type,
                type='service',
                title=title,
                abstract=abstract,
                keywords=keywords,
                wkt_geometry=self.wkt_geometry,
                srs=srs
            )
            anytexts = gen_anytext(title, abstract, keywords)
            Service.objects.filter(id=self.id).update(anytext=anytexts, xml=xml, csw_type='service')
        except Exception as err:
            print(err)
            message = str(err)
            success = False

        end_time = datetime.datetime.utcnow()
        delta = end_time - start_time
        response_time = '%s.%s' % (delta.seconds, delta.microseconds)

        check = Check(
            resource=self,
            success=success,
            response_time=response_time,
            message=message
        )
        check.save()
        print 'Service checked in %s seconds, status is %s' % (response_time, success)


class SpatialReferenceSystem(models.Model):
    """
    SpatialReferenceSystem represents a spatial reference system.
    """
    code = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.code


class Catalog(models.Model):
    """
    Represents a collection of layers to be searched.
    """
    name = models.CharField(
        max_length=255
    )
    slug = AutoSlugField(
        populate_from='name'
    )

    def __unicode__(self):
        return self.name

class Layer(Resource):
    """
    Service represents a remote layer.
    """
    name = models.CharField(max_length=255, null=True, blank=True)
    # bbox should be in WGS84
    bbox_x0 = models.DecimalField(max_digits=19, decimal_places=10, blank=True, null=True)
    bbox_x1 = models.DecimalField(max_digits=19, decimal_places=10, blank=True, null=True)
    bbox_y0 = models.DecimalField(max_digits=19, decimal_places=10, blank=True, null=True)
    bbox_y1 = models.DecimalField(max_digits=19, decimal_places=10, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='layers', blank=True, null=True)
    page_url = models.URLField(max_length=255)
    srs = models.ManyToManyField(SpatialReferenceSystem)
    service = models.ForeignKey(Service)
    catalogs = models.ManyToManyField(Catalog)

    def __unicode__(self):
        return '%s - %s' % (self.id, self.name)

    def get_url_endpoint(self):
        """
        Returns the Hypermap endpoint for a layer.
        This endpoint will be the WMTS MapProxy endpoint, only for WM and Esri we use original endpoints.
        """
        endpoint = self.url
        if self.type not in ('WM', 'ESRI:ArcGIS:MapServer', 'ESRI:ArcGIS:ImageServer'):
            endpoint = '%slayer/%s/map/wmts/1.0.0/WMTSCapabilities.xml' % (settings.SITE_URL, self.id)
        return endpoint

    def get_tile_url(self):
        """
        Returns the tile url MapProxy endpoint for the layer.
        """
        if self.type not in ('WM', 'ESRI:ArcGIS:MapServer', 'ESRI:ArcGIS:ImageServer'):
            return '/layers/%s/map/wmts/nypl_map/default_grid/{z}/{y}/{x}.png' % self.id
        else:
            return None

    def has_valid_bbox(self):
        if self.bbox_x0 is None or self.bbox_y0 is None or self.bbox_x1 is None or self.bbox_y1 is None:
            return False
        else:
            if self.bbox_x0 > self.bbox_x1 or self.bbox_y0 > self.bbox_y1:
                return False
            else:
                return True

    def get_layer_dates(self):
        dates = []
        if hasattr(self, 'layerwm'):
            if self.layerwm.temporal_extent_start:
                pydate = get_parsed_date(self.layerwm.temporal_extent_start)
                if pydate:
                    start_date = []
                    start_date.append(pydate)
                    start_date.append(1)
                    dates.append(start_date)
            if self.layerwm.temporal_extent_start:
                pydate = get_parsed_date(self.layerwm.temporal_extent_end)
                if pydate:
                    end_date = []
                    end_date.append(pydate)
                    end_date.append(1)
                    dates.append(end_date)
        for layerdate in self.layerdate_set.all().order_by('date'):
            sdate = layerdate.date
            if 'TO' not in sdate:
                pydate = get_parsed_date(sdate)
                if pydate:
                    date = []
                    date.append(pydate)
                    date.append(layerdate.type)
                    dates.append(date)
        return dates

    def update_thumbnail(self):
        print 'Generating thumbnail for layer id %s' % self.id
        if not self.has_valid_bbox():
            raise ValueError('Extent for this layer is invalid, cannot generate thumbnail')
            return None
        format_error_message = 'This layer does not expose valid formats (png, jpeg) to generate the thumbnail'
        img = None
        if self.type == 'OGC:WMS':
            ows = WebMapService(self.service.url)
            op_getmap = ows.getOperationByName('GetMap')
            image_format = 'image/png'
            if image_format not in op_getmap.formatOptions:
                if 'image/jpeg' in op_getmap.formatOptions:
                    image_format = 'image/jpeg'
                else:
                    raise NotImplementedError(format_error_message)
            img = ows.getmap(
                layers=[self.name],
                srs='EPSG:4326',
                bbox=(
                    float(self.bbox_x0),
                    float(self.bbox_y0),
                    float(self.bbox_x1),
                    float(self.bbox_y1)
                ),
                size=(50, 50),
                format=image_format,
                transparent=True
            )
            if 'ogc.se_xml' in img.info()['Content-Type']:
                raise ValueError(img.read())
                img = None
        elif self.type == 'OGC:WMTS':

            ows = WebMapTileService(self.service.url)
            ows_layer = ows.contents[self.name]
            image_format = 'image/png'
            if image_format not in ows_layer.formats:
                if 'image/jpeg' in ows_layer.formats:
                    image_format = 'image/jpeg'
                else:
                    raise NotImplementedError(format_error_message)
            img = ows.gettile(
                                layer=self.name,
                                tilematrixset=ows_layer.tilematrixsets[0],
                                tilematrix='0',
                                row='0',
                                column='0',
                                format=image_format
                            )
        elif self.type == 'WM':
            ows = WebMapService(self.url, username=settings.WM_USERNAME, password=settings.WM_PASSWORD)
            op_getmap = ows.getOperationByName('GetMap')
            image_format = 'image/png'
            if image_format not in op_getmap.formatOptions:
                if 'image/jpeg' in op_getmap.formatOptions:
                    image_format = 'image/jpeg'
                else:
                    raise NotImplementedError(format_error_message)
            img = ows.getmap(
                layers=[self.name],
                srs='EPSG:4326',
                bbox=(
                    float(self.bbox_x0),
                    float(self.bbox_y0),
                    float(self.bbox_x1),
                    float(self.bbox_y1)
                ),
                size=(50, 50),
                format=image_format,
                transparent=True
            )
            if 'ogc.se_xml' in img.info()['Content-Type']:
                raise ValueError(img.read())
                img = None
        elif self.type == 'WARPER':
            ows = WebMapService(self.url)
            op_getmap = ows.getOperationByName('GetMap')
            image_format = 'image/png'
            if image_format not in op_getmap.formatOptions:
                if 'image/jpeg' in op_getmap.formatOptions:
                    image_format = 'image/jpeg'
                else:
                    raise NotImplementedError(format_error_message)
            img = ows.getmap(
                layers=[self.name],
                srs='EPSG:4326',
                bbox=(
                    float(self.bbox_x0),
                    float(self.bbox_y0),
                    float(self.bbox_x1),
                    float(self.bbox_y1)
                ),
                size=(50, 50),
                format=image_format,
                transparent=True
            )
            if 'ogc.se_xml' in img.info()['Content-Type']:
                raise ValueError(img.read())
                img = None
        elif self.type == 'ESRI:ArcGIS:MapServer':
            try:
                image = None
                arcserver = ArcMapService(self.service.url)
                bbox = '%s, %s, %s, %s' % (
                    float(self.bbox_x0),
                    float(self.bbox_y0),
                    float(self.bbox_x1),
                    float(self.bbox_y1)
                )

                image = arcserver.ExportMap(
                    bbox=bbox,
                    layers='show:' + self.name,
                    transparent='true',
                    dpi='96',
                    format='jpg'
                )
            except Exception, e:
                print e
            name = re.sub('[^\w\-_\. ]', '_', self.name)
            thumbnail_file_name = '%s%s.jpg' % ('/tmp/', name)
            image.save(thumbnail_file_name)
            img = open(thumbnail_file_name, 'r')
            os.remove(thumbnail_file_name)
        elif self.type == 'ESRI:ArcGIS:ImageServer':
            image = None
            try:
                arcserver = ArcImageService(self.service.url)
                bbox = (
                    str(self.bbox_x0) + ',' +
                    str(self.bbox_y0) + ',' +
                    str(self.bbox_x1) + ',' +
                    str(self.bbox_y1)
                )
                image = arcserver.ExportImage(bbox=bbox)
            except Exception, e:
                print e
            name = re.sub('[^\w\-_\. ]', '_', self.name)
            thumbnail_file_name = '%s%s.jpg' % ('/tmp/', name)
            image.save(thumbnail_file_name)
            img = open(thumbnail_file_name, 'r')
            os.remove(thumbnail_file_name)

        # update thumb in model
        if img:
            thumbnail_file_name = '%s.jpg' % self.name
            upfile = SimpleUploadedFile(thumbnail_file_name, img.read(), "image/jpeg")
            self.thumbnail.save(thumbnail_file_name, upfile, True)
            print 'Thumbnail updated for layer %s' % self.name

    def check_available(self):
        """
        Check for availability of a layer and provide run metrics.
        """
        success = True
        start_time = datetime.datetime.utcnow()
        message = ''
        print 'Checking layer id %s' % self.id
        try:
            signals.post_save.disconnect(layer_post_save, sender=Layer)
            self.update_thumbnail()
            if settings.SEARCH_ENABLED:
                if not settings.SKIP_CELERY_TASK:
                    index_layer.delay(self)
                else:
                    index_layer(self)
            signals.post_save.connect(layer_post_save, sender=Layer)

        except Exception, err:
            message = str(err)
            success = False

        end_time = datetime.datetime.utcnow()

        delta = end_time - start_time
        response_time = '%s.%s' % (delta.seconds, delta.microseconds)

        check = Check(
            resource=self,
            success=success,
            response_time=response_time,
            message=message
        )
        check.save()
        print 'Layer checked in %s seconds, status is %s' % (response_time, success)
        return success, message

    def get_absolute_url(self):
        return reverse('layer_detail', args=(self.id,))

    def get_catalogs_slugs(self):
        return list(
            self.catalogs.all().values_list("slug", flat=True)
        )


class LayerDate(models.Model):
    """
    LayerDate represents list of dates that can be used to depict a layer.
    """
    date = models.CharField(max_length=25)
    type = models.IntegerField(choices=DATE_TYPES)
    layer = models.ForeignKey(Layer)

    def __unicode__(self):
        return self.date


class LayerWM(models.Model):
    """
    LayerWM represents the extended attributes that are found in a WorldMap layer.
    """
    category = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    temporal_extent_start = models.CharField(max_length=255, null=True, blank=True)
    temporal_extent_end = models.CharField(max_length=255, null=True, blank=True)
    layer = models.OneToOneField(Layer)

    def __unicode__(self):
        return self.layer.name

    class Meta:
        verbose_name = 'WorldMap Layer Attributes'
        verbose_name_plural = 'WorldMap Layers Attributes'


class Check(models.Model):
    """
    Check represents the measurement of resource (service/layer) state.
    """
    resource = models.ForeignKey(Resource)
    checked_datetime = models.DateTimeField(auto_now=True)
    success = models.BooleanField(default=False)
    response_time = models.FloatField()
    message = models.TextField(default='OK')

    def __unicode__(self):
        return 'Check %s' % self.id


class EndpointList(models.Model):
    """
    EndpointList represents a file containing an EndPoint list.
    """
    upload = models.FileField(upload_to='endpoint_lists')

    def __unicode__(self):
        return self.upload.name

    def endpoints_admin_url(self):
        url = '<a href="/admin/aggregator/endpoint/?endpoint_list=%s">Endpoints for this list</a>' % self.id
        return url
    endpoints_admin_url.allow_tags = True


class Endpoint(models.Model):
    """
    Endpoint represents a url containing an end point and its status.
    """
    processed = models.BooleanField(default=False)
    processed_datetime = models.DateTimeField(auto_now=True)
    imported = models.BooleanField(default=False)
    message = models.TextField(blank=True, null=True)
    url = models.URLField(unique=True, max_length=255)
    endpoint_list = models.ForeignKey(EndpointList)


class TaskError(models.Model):
    """
    TaskError represents a task error, until we find a better way to handle this with Celery.
    """
    task_name = models.CharField(max_length=255)
    args = models.CharField(max_length=255)
    error_datetime = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)


def bbox2wktpolygon(bbox):
    """
    Return OGC WKT Polygon of a simple bbox list
    """

    minx = float(bbox[0])
    miny = float(bbox[1])
    maxx = float(bbox[2])
    maxy = float(bbox[3])
    return 'POLYGON((%.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f))' \
        % (minx, miny, minx, maxy, maxx, maxy, maxx, miny, minx, miny)


def create_metadata_record(**kwargs):
    """
    Create a csw:Record XML document from harvested metadata
    """

    if 'srs' in kwargs:
        srs = kwargs['srs']
    else:
        srs = '4326'

    modified = '%sZ' % datetime.datetime.utcnow().isoformat().split('.')[0]

    nsmap = Namespaces().get_namespaces(['csw', 'dc', 'dct', 'ows'])

    e = etree.Element(nspath_eval('csw:Record', nsmap), nsmap=nsmap)

    etree.SubElement(e, nspath_eval('dc:identifier', nsmap)).text = kwargs['identifier']
    etree.SubElement(e, nspath_eval('dc:title', nsmap)).text = kwargs['title']
    etree.SubElement(e, nspath_eval('dct:modified', nsmap)).text = modified
    etree.SubElement(e, nspath_eval('dct:abstract', nsmap)).text = kwargs['abstract']
    etree.SubElement(e, nspath_eval('dc:type', nsmap)).text = kwargs['type']
    etree.SubElement(e, nspath_eval('dc:format', nsmap)).text = kwargs['format']
    etree.SubElement(e, nspath_eval('dc:source', nsmap)).text = kwargs['source']

    if 'relation' in kwargs:
        etree.SubElement(e, nspath_eval('dc:relation', nsmap)).text = kwargs['relation']

    if 'keywords' in kwargs:
        for keyword in kwargs['keywords']:
            etree.SubElement(e, nspath_eval('dc:subject', nsmap)).text = keyword

    for link in kwargs['links']:
        etree.SubElement(e, nspath_eval('dct:references', nsmap), scheme=link[0]).text = link[1]

    bbox2 = loads(kwargs['wkt_geometry']).bounds
    bbox = etree.SubElement(e, nspath_eval('ows:BoundingBox', nsmap),
                            crs='http://www.opengis.net/def/crs/EPSG/0/%s' % srs,
                            dimensions='2')

    etree.SubElement(bbox, nspath_eval('ows:LowerCorner', nsmap)).text = '%s %s' % (bbox2[1], bbox2[0])
    etree.SubElement(bbox, nspath_eval('ows:UpperCorner', nsmap)).text = '%s %s' % (bbox2[3], bbox2[2])

    return etree.tostring(e, pretty_print=True)


def gen_anytext(*args):
    """
    Convenience function to create bag of words for anytext property
    """

    bag = []

    for term in args:
        if term is not None:
            if isinstance(term, list):
                for term2 in term:
                    if term is not None:
                        bag.append(term2)
            else:
                bag.append(term)
    return ' '.join(bag)


def endpointlist_post_save(instance, *args, **kwargs):
    """
    Used to process the lines of the endpoint list.
    """
    f = instance.upload
    f.open(mode='rb')
    lines = f.readlines()
    for url in lines:
        if len(url) > 255:
            print 'Skipping this enpoint, as it is more than 255 characters: %s' % url
        else:
            if Endpoint.objects.filter(url=url).count() == 0:
                endpoint = Endpoint(url=url, endpoint_list=instance)
                endpoint.save()
    f.close()
    if not settings.SKIP_CELERY_TASK:
        update_endpoints.delay(instance)
    else:
        update_endpoints(instance)


def service_pre_save(instance, *args, **kwargs):
    """
    Used to do a service full check when saving it.
    """
    # for some service we need to constraint some default values
    if instance.type == 'WM':
        instance.title = 'Harvard WorldMap'
        instance.url = 'http://worldmap.harvard.edu/'
    # check if service is unique
    # we cannot use unique_together as it relies on a combination of fields
    # from different models (service, resource)
    if Service.objects.filter(url=instance.url, type=instance.type).count() > 0:
        raise Exception("There is already such a service")


def service_post_save(instance, *args, **kwargs):
    """
    Used to do a service full check when saving it.
    """
    # check service
    if not settings.SKIP_CELERY_TASK:
        check_service.delay(instance)
    else:
        check_service(instance)


def layer_post_save(instance, *args, **kwargs):
    """
    Used to do a layer full check when saving it.
    """
    if not settings.SKIP_CELERY_TASK:
        check_layer.delay(instance)
    else:
        check_layer(instance)


signals.post_save.connect(endpointlist_post_save, sender=EndpointList)
signals.pre_save.connect(service_pre_save, sender=Service)
signals.post_save.connect(service_post_save, sender=Service)
signals.post_save.connect(layer_post_save, sender=Layer)
