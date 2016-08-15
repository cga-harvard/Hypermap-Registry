import datetime
import os
import re
import json
import urllib2
import requests
from urlparse import urlparse
from dateutil.parser import parse

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db.models import Avg, Min, Max
from django.db.models import signals
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django_extensions.db.fields import AutoSlugField

from taggit.managers import TaggableManager
from lxml import etree
from shapely.wkt import loads
from owslib.namespaces import Namespaces
from owslib.util import nspath_eval
from owslib.csw import CatalogueServiceWeb
from owslib.tms import TileMapService
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
from arcrest import MapService as ArcMapService, ImageService as ArcImageService

from enums import CSW_RESOURCE_TYPES, SERVICE_TYPES, DATE_TYPES
from tasks import update_endpoint, update_endpoints, check_service, check_layer, index_layer
from utils import get_esri_extent, get_esri_service_name, format_float, flip_coordinates

from hypermap.dynasty.utils import get_mined_dates

REGISTRY_LIMIT_LAYERS = getattr(settings, 'REGISTRY_LIMIT_LAYERS', -1)

if REGISTRY_LIMIT_LAYERS > 0:
    DEBUG_SERVICES = True
    DEBUG_LAYER_NUMBER = REGISTRY_LIMIT_LAYERS
else:
    DEBUG_SERVICES = False
    DEBUG_LAYER_NUMBER = -1


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


def add_metadata_dates_to_layer(dates, layer):
    default = datetime.datetime(2016, 1, 1)
    for date in dates:
        if date:
            date = '%s' % date
            if date != '':
                if date.startswith('-'):
                    layerdate, created = LayerDate.objects.get_or_create(layer=layer, date=date, type=1)
                else:
                    try:
                        dt = parse(date, default=default)
                        if dt:
                            iso = dt.isoformat()
                            tokens = iso.strip().split("T")
                            fdate = tokens[0]
                            print 'Adding date %s to layer %s' % (fdate, layer.id)
                            layerdate, created = LayerDate.objects.get_or_create(layer=layer, date=fdate, type=1)
                        else:
                            print 'Skipping date "%s" as is invalid.' % date
                    except:
                        print 'Skipping date "%s" as is invalid.' % date


def add_mined_dates(layer):
    text_to_mine = ''
    if layer.title:
        text_to_mine = text_to_mine + layer.title
    if layer.abstract:
        text_to_mine = text_to_mine + ' ' + layer.abstract
    mined_dates = get_mined_dates(text_to_mine)
    for date in mined_dates:
        layer.layerdate_set.get_or_create(date=date, type=0)


class SpatialReferenceSystem(models.Model):
    """
    SpatialReferenceSystem represents a spatial reference system.
    """
    code = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.code


class Check(models.Model):
    """
    Check represents the measurement of resource (service/layer) state.
    """
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    checked_datetime = models.DateTimeField(auto_now=True)
    success = models.BooleanField(default=False)
    response_time = models.FloatField()
    message = models.TextField(default='OK')

    def __unicode__(self):
        return 'Check %s' % self.id


class Resource(models.Model):
    """
    Resource represents basic information for a resource (service/layer).
    """
    title = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    keywords = TaggableManager(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    url = models.URLField(max_length=255)
    is_public = models.BooleanField(default=True)
    type = models.CharField(max_length=32, choices=SERVICE_TYPES)

    check_set = generic.GenericRelation(Check, object_id_field='object_id')

    temporal_extent_start = models.CharField(max_length=255, null=True, blank=True)
    temporal_extent_end = models.CharField(max_length=255, null=True, blank=True)

    # CSW fields
    csw_last_updated = models.CharField(max_length=32,
                                        default=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                                        null=True, blank=True)
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
        return str(self.id)

    class Meta:
        abstract = True

    @property
    def id_string(self):
        return str(self.id)

    @property
    def keywords_csv(self):
        keywords_qs = self.keywords.all()
        if keywords_qs:
            return ','.join([kw.name for kw in keywords_qs])
        else:
            return ''

    @property
    def last_updated_iso8601(self):
        if self.last_updated:
            iso8601 = self.last_updated.isoformat()
            if not self.last_updated.utcoffset:
                return '%sZ' % iso8601
            return iso8601

    @property
    def csw_resourcetype(self):
        return CSW_RESOURCE_TYPES[self.type]

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
        # TODO: exclude failed checks with response time = 0.0
        return self.check_set.aggregate(Avg('response_time')).values()[0]

    @property
    def min_response_time(self):
        # TODO: exclude failed checks with response time = 0.0
        return self.check_set.aggregate(Min('response_time')).values()[0]

    @property
    def max_response_time(self):
        # TODO: exclude failed checks with response time = 0.0
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

    def get_checks_admin_url(self):
        path = reverse("admin:%s_%s_changelist" % (self._meta.app_label, "check"))
        return path

    def get_checks_admin_reliability_warning_url(self):
        """
        When service Realiability is going down users should go to the
        the check history to find problem causes.
        :return: admin url with check list for this instance
        """
        # TODO: cache this.
        path = self.get_checks_admin_url()
        content_type = ContentType.objects.get_for_model(self)
        params = "?content_type__id__exact={0}&q={1}&success__exact=0".format(
            content_type.id,
            self.id
        )
        url = path + params
        return url


class Service(Resource):
    """
    Service represents a remote geowebservice.
    """

    srs = models.ManyToManyField(SpatialReferenceSystem, blank=True)
    catalog = models.ForeignKey("Catalog", editable=False, default=1)

    @property
    def get_domain(self):
        parsed_uri = urlparse(self.url)
        domain = '{uri.netloc}'.format(uri=parsed_uri)
        return domain

    @property
    def get_absolute_url(self):
        return reverse("service_detail", args=[self.catalog.slug, self.id])

    def update_layers(self):
        """
        Update layers for a service.
        """
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
        elif self.type == 'Hypermap:WorldMap':
            update_layers_wm(self)
        elif self.type == 'Hypermap:WARPER':
            update_layers_warper(self)
        signals.post_save.connect(layer_post_save, sender=Layer)

    def index_layers(self):
        """
        Index all layers for this service.
        """
        if settings.REGISTRY_SEARCH_URL is not None:
            for layer in self.layer_set.all():
                index_layer(layer)

    def check_available(self):
        """
        Check for availability of a service and provide run metrics.
        """
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
            if self.type == 'OGC:CSW':
                ows = CatalogueServiceWeb(self.url)
                title = ows.identification.title
                abstract = ows.identification.abstract
                keywords = ows.identification.keywords
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
            if self.type == 'OSGeo:TMS':
                ows = TileMapService(self.url)
                title = ows.identification.title
                abstract = ows.identification.abstract
                keywords = ows.identification.keywords
            if self.type == 'ESRI:ArcGIS:MapServer':
                esri = ArcMapService(self.url)
                extent, srs = get_esri_extent(esri)
                title = esri.mapName
                if len(title) == 0:
                    title = get_esri_service_name(self.url)
                wkt_geometry = bbox2wktpolygon([
                    extent['xmin'],
                    extent['ymin'],
                    extent['xmax'],
                    extent['ymax']
                ])
            if self.type == 'ESRI:ArcGIS:ImageServer':
                esri = ArcImageService(self.url)
                extent, srs = get_esri_extent(esri)
                title = esri._json_struct['name']
                if len(title) == 0:
                    title = get_esri_service_name(self.url)
                wkt_geometry = bbox2wktpolygon([
                    extent['xmin'],
                    extent['ymin'],
                    extent['xmax'],
                    extent['ymax']
                ])
            if self.type == 'Hypermap:WorldMap':
                urllib2.urlopen(self.url)
                title = 'Harvard WorldMap'
            if self.type == 'Hypermap:WARPER':
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
            content_object=self,
            success=success,
            response_time=response_time,
            message=message
        )
        check.save()
        print 'Service checked in %s seconds, status is %s' % (response_time, success)


class Catalog(models.Model):
    """
    Represents a collection of layers to be searched.
    """
    name = models.CharField(
        max_length=255,
        help_text="Display name in UI"
    )
    slug = AutoSlugField(
        populate_from='name',
        editable=True,
        help_text="Leave empty to be populated from name"
    )
    url = models.URLField(
        max_length=255,
        help_text=("Only if remote. URL where the API for the search backend is served."
                   "ex: http://localhost:8000/registry/api/search/"),
        null=True, blank=True
    )

    def __unicode__(self):
        return '{0}'.format(
            self.name
        )

    def get_search_url(self):
        """
        resolve the search url no matter if local or remote.
        :return: url or exception
        """

        if self.is_remote:
            return self.url

        return reverse('search_api', args=[self.slug])

    @property
    def is_remote(self):
        """
        Define if data source is local or remote
        :return: True if remote, else False.
        """
        if self.url and len(self.url) > 0:
            return True
        return False

    def get_absolute_url(self):
        return reverse('index', args=[self.slug])


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
    page_url = models.URLField(max_length=255, blank=True, null=True)
    service = models.ForeignKey(Service, blank=True, null=True)
    is_monitored = models.BooleanField(default=True)
    catalog = models.ForeignKey(Catalog, editable=False, default=1)

    def __unicode__(self):
        return '%s' % self.id

    def get_url_endpoint(self):
        """
        Returns the Hypermap endpoint for a layer.
        This endpoint will be the WMTS MapProxy endpoint, only for WM we use the original endpoint.
        """
        endpoint = self.url
        if self.type not in ('Hypermap:WorldMap',):
            endpoint = '%s/registry/%s/layer/%s/map/wmts/1.0.0/WMTSCapabilities.xml' % (
                settings.SITE_URL.rstrip('/'),
                self.catalog.slug,
                self.id
            )
        return endpoint

    def get_tile_url(self):
        """
        Returns the tile url MapProxy endpoint for the layer.
        """
        if self.type not in ('Hypermap:WorldMap',):
            return '/registry/%s/layer/%s/map/wmts/%s/default_grid/{z}/{y}/{x}.png' % (
                   self.catalog.slug, self.id, self.name)
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

        def get_date_sign(a_date):
            sign = '+'
            if sdate[0] == '-':
                sign = '-'
            return sign

        # string must be parsed, and check if they have a negative value in front of it
        dates = []
        # get dates from layerwm
        if hasattr(self, 'layerwm'):
            if self.layerwm.temporal_extent_start:
                sdate = self.layerwm.temporal_extent_start
                pydate = get_parsed_date(sdate)
                if pydate:
                    start_date = []
                    start_date.append(get_date_sign(sdate))
                    start_date.append(pydate)
                    start_date.append(1)
                    dates.append(start_date)
            if self.layerwm.temporal_extent_end:
                sdate = self.layerwm.temporal_extent_end
                pydate = get_parsed_date(sdate)
                if pydate:
                    end_date = []
                    end_date.append(get_date_sign(sdate))
                    end_date.append(pydate)
                    end_date.append(1)
                    dates.append(end_date)
        # now we return all the other dates
        for layerdate in self.layerdate_set.all().order_by('date'):
            sdate = layerdate.date
            # for now we skip ranges
            if 'TO' not in sdate:
                pydate = get_parsed_date(sdate)
                if pydate:
                    date = []
                    date.append(get_date_sign(sdate))
                    date.append(pydate)
                    date.append(layerdate.type)
                    dates.append(date)
        print dates
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
        elif self.type == 'Hypermap:WorldMap':
            ows = WebMapService(self.url,
                                username=settings.REGISTRY_WORLDMAP_USERNAME,
                                password=settings.REGISTRY_WORLDMAP_PASSWORD)
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
        elif self.type == 'Hypermap:WARPER':
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
            img = open(thumbnail_file_name)
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
            img = open(thumbnail_file_name)
            os.remove(thumbnail_file_name)

        # update thumb in model
        if img and hasattr(img, 'close'):
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
            if settings.REGISTRY_SEARCH_URL is not None:
                if not settings.REGISTRY_SKIP_CELERY:
                    index_layer.delay(self)
                else:
                    index_layer(self)
            signals.post_save.connect(layer_post_save, sender=Layer)

        except ValueError, err:
            # caused by update_thumbnail()
            # self.href is empty in arcserver.ExportMap
            if str(err).startswith("unknown url type:"):
                print 'Thumbnail can not be updated: %s' % str(err)
        except Exception, err:
            message = str(err)
            success = False

        end_time = datetime.datetime.utcnow()

        delta = end_time - start_time
        response_time = '%s.%s' % (delta.seconds, delta.microseconds)

        check = Check(
            content_object=self,
            success=success,
            response_time=response_time,
            message=message
        )
        check.save()
        print 'Layer checked in %s seconds, status is %s' % (response_time, success)
        return success, message

    @property
    def get_absolute_url(self):
        return '{0}{1}'.format(
            settings.SITE_URL,
            reverse("layer_detail", args=[self.catalog.slug, self.id])
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


class EndpointList(models.Model):
    """
    EndpointList represents a file containing an EndPoint list.
    """
    upload = models.FileField(upload_to='endpoint_lists')
    greedy = models.BooleanField(default=False)
    catalog = models.ForeignKey(Catalog, editable=False, default=1)

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
    url = models.URLField(max_length=255)
    endpoint_list = models.ForeignKey(EndpointList, blank=True, null=True)
    catalog = models.ForeignKey(Catalog, editable=False, default=1)

    class Meta:
        unique_together = ("url", "catalog")

    @property
    def id_string(self):
        return str(self.id)


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
    if 'alternative' in kwargs:
        etree.SubElement(e, nspath_eval('dct:alternative', nsmap)).text = kwargs['alternative']
    etree.SubElement(e, nspath_eval('dct:modified', nsmap)).text = modified
    etree.SubElement(e, nspath_eval('dct:abstract', nsmap)).text = kwargs['abstract']
    etree.SubElement(e, nspath_eval('dc:type', nsmap)).text = kwargs['type']
    etree.SubElement(e, nspath_eval('dc:format', nsmap)).text = kwargs['format']
    etree.SubElement(e, nspath_eval('dc:source', nsmap)).text = kwargs['source']

    if 'relation' in kwargs:
        etree.SubElement(e, nspath_eval('dc:relation', nsmap)).text = kwargs['relation']

    if 'keywords' in kwargs:
        if kwargs['keywords'] is not None:
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
                    if term2 is not None:
                        bag.append(term2)
            else:
                bag.append(term)
    return ' '.join(bag)


# updatelayers for each service type

def update_layers_wms(service):
    """
    Update layers for an OGC:WMS service.
    Sample endpoint: http://demo.geonode.org/geoserver/ows
    """
    try:
        wms = WebMapService(service.url)
        layer_names = list(wms.contents)
        parent = wms.contents[layer_names[0]].parent
        # fallback, some endpoint like this one:
        # https://nsidc.org/cgi-bin/atlas_north?service=WMS&request=GetCapabilities&version=1.1.1
        # does not have a parent to check for srs
        if parent:
            crsOptions = parent.crsOptions
        else:
            crsOptions = wms.contents[layer_names[0]].crsOptions
        # set srs
        for crs_code in crsOptions:
            srs, created = SpatialReferenceSystem.objects.get_or_create(code=crs_code)
            service.srs.add(srs)

        # now update layers
        layer_n = 0
        total = len(layer_names)
        for layer_name in layer_names:
            ows_layer = wms.contents[layer_name]
            print 'Updating layer %s' % ows_layer.name
            # get or create layer
            layer, created = Layer.objects.get_or_create(name=ows_layer.name, service=service, catalog=service.catalog)
            if layer.active:
                links = [['OGC:WMS', service.url]]
                # update fields
                layer.type = 'OGC:WMS'
                layer.title = ows_layer.title
                layer.abstract = ows_layer.abstract
                layer.url = service.url
                layer.page_url = layer.get_absolute_url
                links.append([
                    'WWW:LINK',
                    settings.SITE_URL.rstrip('/') + layer.page_url
                ])
                # bbox
                bbox = list(ows_layer.boundingBoxWGS84 or (-179.0, -89.0, 179.0, 89.0))
                layer.bbox_x0 = bbox[0]
                layer.bbox_y0 = bbox[1]
                layer.bbox_x1 = bbox[2]
                layer.bbox_y1 = bbox[3]
                layer.wkt_geometry = bbox2wktpolygon(bbox)
                # keywords
                for keyword in ows_layer.keywords:
                    layer.keywords.add(keyword)
                # crsOptions
                # TODO we may rather prepopulate with fixutres the SpatialReferenceSystem table
                layer.xml = create_metadata_record(
                    identifier=layer.id_string,
                    source=service.url,
                    links=links,
                    format='OGC:WMS',
                    type=layer.csw_type,
                    relation=service.id_string,
                    title=ows_layer.title,
                    alternative=ows_layer.name,
                    abstract=ows_layer.abstract,
                    keywords=ows_layer.keywords,
                    wkt_geometry=layer.wkt_geometry
                )
                layer.anytext = gen_anytext(layer.title, layer.abstract, ows_layer.keywords)
                layer.save()
                # dates
                add_mined_dates(layer)
            layer_n = layer_n + 1
            # exits if DEBUG_SERVICES
            print "Updating layer n. %s/%s" % (layer_n, total)
            if DEBUG_SERVICES and layer_n == DEBUG_LAYER_NUMBER:
                return
    except Exception as err:
        message = "update_layers_wms: {0}".format(
            err
        )
        check = Check(
            content_object=service,
            success=False,
            response_time=0,
            message=message
        )
        check.save()


def update_layers_wmts(service):
    """
    Update layers for an OGC:WMTS service.
    Sample endpoint: http://map1.vis.earthdata.nasa.gov/wmts-geo/1.0.0/WMTSCapabilities.xml
    """
    try:
        wmts = WebMapTileService(service.url)

        # set srs
        # WMTS is always in 4326
        srs, created = SpatialReferenceSystem.objects.get_or_create(code='EPSG:4326')
        service.srs.add(srs)

        layer_names = list(wmts.contents)
        layer_n = 0
        total = len(layer_names)
        for layer_name in layer_names:
            ows_layer = wmts.contents[layer_name]
            print 'Updating layer %s' % ows_layer.name
            layer, created = Layer.objects.get_or_create(name=ows_layer.name, service=service, catalog=service.catalog)
            if layer.active:
                links = [['OGC:WMTS', service.url]]
                layer.type = 'OGC:WMTS'
                layer.title = ows_layer.title
                layer.abstract = ows_layer.abstract
                # keywords
                # @tomkralidis wmts does not seem to support this attribute
                keywords = None
                if hasattr(ows_layer, 'keywords'):
                    keywords = ows_layer.keywords
                    for keyword in keywords:
                        layer.keywords.add(keyword)
                layer.url = service.url
                layer.page_url = layer.get_absolute_url
                links.append([
                    'WWW:LINK',
                    settings.SITE_URL.rstrip('/') + layer.page_url
                ])
                bbox = list(ows_layer.boundingBoxWGS84 or (-179.0, -89.0, 179.0, 89.0))
                layer.bbox_x0 = bbox[0]
                layer.bbox_y0 = bbox[1]
                layer.bbox_x1 = bbox[2]
                layer.bbox_y1 = bbox[3]
                layer.wkt_geometry = bbox2wktpolygon(bbox)
                layer.xml = create_metadata_record(
                    identifier=layer.id_string,
                    source=service.url,
                    links=links,
                    format='OGC:WMS',
                    type=layer.csw_type,
                    relation=service.id_string,
                    title=ows_layer.title,
                    alternative=ows_layer.name,
                    abstract=layer.abstract,
                    keywords=keywords,
                    wkt_geometry=layer.wkt_geometry
                )
                layer.anytext = gen_anytext(layer.title, layer.abstract, keywords)
                layer.save()
                # dates
                add_mined_dates(layer)
            layer_n = layer_n + 1
            # exits if DEBUG_SERVICES
            print "Updating layer n. %s/%s" % (layer_n, total)
            if DEBUG_SERVICES and layer_n == DEBUG_LAYER_NUMBER:
                return
    except Exception as err:
        message = "update_layers_wmts: {0}".format(
            err
        )
        check = Check(
            content_object=service,
            success=False,
            response_time=0,
            message=message
        )
        check.save()


def update_layers_wm(service):
    """
    Update layers for an WorldMap.
    Sample endpoint: http://worldmap.harvard.edu/
    """

    try:
        response = requests.get('http://worldmap.harvard.edu/data/search/api?start=0&limit=10')
        data = json.loads(response.content)
        total = data['total']

        # set srs
        # WorldMap supports only 4326, 900913, 3857
        for crs_code in ['EPSG:4326', 'EPSG:900913', 'EPSG:3857']:
            srs, created = SpatialReferenceSystem.objects.get_or_create(code=crs_code)
            service.srs.add(srs)

        layer_n = 0
        for i in range(0, total, 10):
            url = 'http://worldmap.harvard.edu/data/search/api?start=%s&limit=10' % i
            print 'Fetching %s' % url
            response = requests.get(url)
            data = json.loads(response.content)
            for row in data['rows']:
                name = row['name']
                title = row['title']
                abstract = row['abstract']
                bbox = row['bbox']
                page_url = row['detail']
                category = ''
                if 'topic_category' in row:
                    category = row['topic_category']
                username = ''
                if 'owner_username' in row:
                    username = row['owner_username']
                temporal_extent_start = ''
                if 'temporal_extent_start' in row:
                    temporal_extent_start = row['temporal_extent_start']
                temporal_extent_end = ''
                if 'temporal_extent_end' in row:
                    temporal_extent_end = row['temporal_extent_end']
                # we use the geoserver virtual layer getcapabilities for wm endpoint
                endpoint = 'http://worldmap.harvard.edu/geoserver/geonode/%s/wms?' % name
                is_public = True
                if '_permissions' in row:
                    if not row['_permissions']['view']:
                        is_public = False
                layer, created = Layer.objects.get_or_create(name=name, service=service, catalog=service.catalog)
                if layer.active:
                    links = [['Hypermap:WorldMap', endpoint]]
                    # update fields
                    layer.type = 'Hypermap:WorldMap'
                    layer.title = title
                    layer.abstract = abstract
                    layer.is_public = is_public
                    layer.url = endpoint
                    layer.page_url = page_url
                    # category and owner username
                    layer_wm, created = LayerWM.objects.get_or_create(layer=layer)
                    layer_wm.category = category
                    layer_wm.username = username
                    layer_wm.temporal_extent_start = temporal_extent_start
                    layer_wm.temporal_extent_end = temporal_extent_end
                    layer_wm.save()
                    # bbox
                    x0 = format_float(bbox['minx'])
                    y0 = format_float(bbox['miny'])
                    x1 = format_float(bbox['maxx'])
                    y1 = format_float(bbox['maxy'])
                    # In many cases for some reason to be fixed GeoServer has x coordinates flipped in WM.
                    x0, x1 = flip_coordinates(x0, x1)
                    y0, y1 = flip_coordinates(y0, y1)
                    layer.bbox_x0 = x0
                    layer.bbox_y0 = y0
                    layer.bbox_x1 = x1
                    layer.bbox_y1 = y1
                    # keywords
                    for keyword in row['keywords']:
                        layer.keywords.add(keyword)

                    layer.wkt_geometry = bbox2wktpolygon((bbox['minx'], bbox['miny'], bbox['maxx'], bbox['maxy']))
                    layer.xml = create_metadata_record(
                        identifier=layer.id_string,
                        source=endpoint,
                        links=links,
                        format='Hypermap:WorldMap',
                        type=layer.csw_type,
                        relation=service.id_string,
                        title=layer.title,
                        alternative=name,
                        abstract=layer.abstract,
                        keywords=row['keywords'],
                        wkt_geometry=layer.wkt_geometry
                    )
                    layer.anytext = gen_anytext(layer.title, layer.abstract, row['keywords'])
                    layer.save()
                    # dates
                    add_mined_dates(layer)
                    add_metadata_dates_to_layer([layer_wm.temporal_extent_start, layer_wm.temporal_extent_end], layer)
                layer_n = layer_n + 1
                # exits if DEBUG_SERVICES
                print "Updating layer n. %s/%s" % (layer_n, total)
                if DEBUG_SERVICES and layer_n == DEBUG_LAYER_NUMBER:
                    return
    except Exception as err:
        message = "update_layers_wm: {0}".format(
            err
        )
        check = Check(
            content_object=service,
            success=False,
            response_time=0,
            message=message
        )
        check.save()


def update_layers_warper(service):
    """
    Update layers for a Warper service.
    Sample endpoint: http://warp.worldmap.harvard.edu/maps
    """
    params = {'field': 'title', 'query': '', 'show_warped': '1', 'format': 'json'}
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    request = requests.get(service.url, headers=headers, params=params)

    try:
        records = json.loads(request.content)
        total_pages = int(records['total_pages'])

        # set srs
        # Warper supports only 4326, 900913, 3857
        for crs_code in ['EPSG:4326', 'EPSG:900913', 'EPSG:3857']:
            srs, created = SpatialReferenceSystem.objects.get_or_create(code=crs_code)
            service.srs.add(srs)

        for i in range(1, total_pages + 1):
            params = {'field': 'title', 'query': '', 'show_warped': '1', 'format': 'json', 'page': i}
            request = requests.get(service.url, headers=headers, params=params)
            records = json.loads(request.content)
            print 'Fetched %s' % request.url
            layers = records['items']
            layer_n = 0
            total = len(layers)
            for layer in layers:
                name = layer['id']
                title = layer['title']
                abstract = layer['description']
                bbox = layer['bbox']
                # dates
                dates = []
                if 'published_date' in layer:
                    dates.append(layer['published_date'])
                if 'date_depicted' in layer:
                    dates.append(layer['date_depicted'])
                if 'depicts_year' in layer:
                    dates.append(layer['depicts_year'])
                if 'issue_year' in layer:
                    dates.append(layer['issue_year'])
                layer, created = Layer.objects.get_or_create(name=name, service=service, catalog=service.catalog)
                if layer.active:
                    # update fields
                    layer.type = 'Hypermap:WARPER'
                    layer.title = title
                    layer.abstract = abstract
                    layer.is_public = True
                    layer.url = '%s/wms/%s?' % (service.url, name)
                    layer.page_url = '%s/%s' % (service.url, name)
                    # bbox
                    x0 = None
                    y0 = None
                    x1 = None
                    y1 = None
                    if bbox:
                        bbox_list = bbox.split(',')
                        x0 = format_float(bbox_list[0])
                        y0 = format_float(bbox_list[1])
                        x1 = format_float(bbox_list[2])
                        y1 = format_float(bbox_list[3])
                    layer.bbox_x0 = x0
                    layer.bbox_y0 = y0
                    layer.bbox_x1 = x1
                    layer.bbox_y1 = y1
                    layer.save()
                    # dates
                    add_mined_dates(layer)
                    add_metadata_dates_to_layer(dates, layer)
                layer_n = layer_n + 1
                # exits if DEBUG_SERVICES
                print "Updating layer n. %s/%s" % (layer_n, total)
                if DEBUG_SERVICES and layer_n == DEBUG_LAYER_NUMBER:
                    return

    except Exception as err:
        message = "update_layers_warper: {0}. request={1} response={2}".format(
            err,
            service.url,
            request.text
        )
        check = Check(
            content_object=service,
            success=False,
            response_time=0,
            message=message
        )
        check.save()


def update_layers_esri_mapserver(service):
    """
    Update layers for an ESRI REST MapServer.
    Sample endpoint: https://gis.ngdc.noaa.gov/arcgis/rest/services/SampleWorldCities/MapServer/?f=json
    """
    try:
        esri_service = ArcMapService(service.url)
        # set srs
        # both mapserver and imageserver exposes just one srs at the service level
        # not sure if other ones are supported, for now we just store this one

        # not sure why this is needed, for now commenting out
        # if wkt_text:
        #     params = {'exact': 'True', 'error': 'True', 'mode': 'wkt', 'terms': wkt_text}
        #     req = requests.get('http://prj2epsg.org/search.json', params=params)
        #     object = json.loads(req.content)
        #     srs = int(object['codes'][0]['code'])

        srs_code = esri_service.spatialReference.wkid
        srs, created = SpatialReferenceSystem.objects.get_or_create(code=srs_code)
        service.srs.add(srs)
        # check if it has a WMS interface
        if 'supportedExtensions' in esri_service._json_struct:
            if 'WMSServer' in esri_service._json_struct['supportedExtensions']:
                # we need to change the url
                # http://cga1.cga.harvard.edu/arcgis/rest/services/ecuador/ecuadordata/MapServer?f=pjson
                # http://cga1.cga.harvard.edu/arcgis/services/ecuador/
                # ecuadordata/MapServer/WMSServer?request=GetCapabilities&service=WMS
                wms_url = service.url.replace('/rest/services/', '/services/')
                if '?f=pjson' in wms_url:
                    wms_url = wms_url.replace('?f=pjson', 'WMSServer?')
                if '?f=json' in wms_url:
                    wms_url = wms_url.replace('?f=json', 'WMSServer?')
                print 'This ESRI REST endpoint has an WMS interface to process: %s' % wms_url
                # import here as otherwise is circular (TODO refactor)
                from utils import create_service_from_endpoint
                create_service_from_endpoint(wms_url, 'OGC:WMS', catalog=service.catalog)
        # now process the REST interface
        layer_n = 0
        total = len(esri_service.layers)
        for esri_layer in esri_service.layers:
            # in some case the json is invalid
            # esri_layer._json_struct
            # {u'currentVersion': 10.01,
            # u'error':
            # {u'message': u'An unexpected error occurred processing the request.', u'code': 500, u'details': []}}
            if 'error' not in esri_layer._json_struct:
                print 'Updating layer %s' % esri_layer.name
                layer, created = Layer.objects.get_or_create(
                    name=esri_layer.id,
                    service=service,
                    catalog=service.catalog
                )
                if layer.active:
                    layer.type = 'ESRI:ArcGIS:MapServer'
                    links = [[layer.type, service.url]]
                    layer.title = esri_layer.name
                    layer.abstract = esri_service.serviceDescription
                    layer.url = service.url
                    layer.page_url = layer.get_absolute_url
                    links.append([
                        'WWW:LINK',
                        settings.SITE_URL.rstrip('/') + layer.page_url
                    ])
                    try:
                        layer.bbox_x0 = esri_layer.extent.xmin
                        layer.bbox_y0 = esri_layer.extent.ymin
                        layer.bbox_x1 = esri_layer.extent.xmax
                        layer.bbox_y1 = esri_layer.extent.ymax
                    except KeyError:
                        pass
                    try:
                        layer.bbox_x0 = esri_layer._json_struct['extent']['xmin']
                        layer.bbox_y0 = esri_layer._json_struct['extent']['ymin']
                        layer.bbox_x1 = esri_layer._json_struct['extent']['xmax']
                        layer.bbox_y1 = esri_layer._json_struct['extent']['ymax']
                    except Exception:
                        pass
                    layer.wkt_geometry = bbox2wktpolygon([layer.bbox_x0, layer.bbox_y0, layer.bbox_x1, layer.bbox_y1])
                    layer.xml = create_metadata_record(
                        identifier=layer.id_string,
                        source=service.url,
                        links=links,
                        format='ESRI:ArcGIS:MapServer',
                        type=layer.csw_type,
                        relation=service.id_string,
                        title=layer.title,
                        alternative=layer.title,
                        abstract=layer.abstract,
                        wkt_geometry=layer.wkt_geometry
                    )
                    layer.anytext = gen_anytext(layer.title, layer.abstract)
                    layer.save()
                    # dates
                    add_mined_dates(layer)
                layer_n = layer_n + 1
                # exits if DEBUG_SERVICES
                print "Updating layer n. %s/%s" % (layer_n, total)
                if DEBUG_SERVICES and layer_n == DEBUG_LAYER_NUMBER:
                    return
    except Exception as err:
        message = "update_layers_esri_mapserver: {0}".format(
            err
        )
        check = Check(
            content_object=service,
            success=False,
            response_time=0,
            message=message
        )
        check.save()


def update_layers_esri_imageserver(service):
    """
    Update layers for an ESRI REST ImageServer.
    Sample endpoint: https://gis.ngdc.noaa.gov/arcgis/rest/services/bag_bathymetry/ImageServer/?f=json
    """
    try:
        esri_service = ArcImageService(service.url)
        # set srs
        # both mapserver and imageserver exposes just one srs at the service level
        # not sure if other ones are supported, for now we just store this one
        obj = json.loads(esri_service._contents)
        srs_code = obj['spatialReference']['wkid']
        srs, created = SpatialReferenceSystem.objects.get_or_create(code=srs_code)
        service.srs.add(srs)
        layer, created = Layer.objects.get_or_create(name=obj['name'], service=service, catalog=service.catalog)
        if layer.active:
            layer.type = 'ESRI:ArcGIS:ImageServer'
            links = [[layer.type, service.url]]
            layer.title = obj['name']
            layer.abstract = esri_service.serviceDescription
            layer.url = service.url
            layer.bbox_x0 = str(obj['extent']['xmin'])
            layer.bbox_y0 = str(obj['extent']['ymin'])
            layer.bbox_x1 = str(obj['extent']['xmax'])
            layer.bbox_y1 = str(obj['extent']['ymax'])
            layer.page_url = layer.get_absolute_url
            links.append([
                'WWW:LINK',
                settings.SITE_URL.rstrip('/') + layer.page_url
            ])
            layer.wkt_geometry = bbox2wktpolygon([layer.bbox_x0, layer.bbox_y0, layer.bbox_x1, layer.bbox_y1])
            layer.xml = create_metadata_record(
                identifier=layer.id_string,
                source=service.url,
                links=links,
                format='ESRI:ArcGIS:ImageServer',
                type=layer.csw_type,
                relation=service.id_string,
                title=layer.title,
                alternative=layer.title,
                abstract=layer.abstract,
                wkt_geometry=layer.wkt_geometry
            )
            layer.anytext = gen_anytext(layer.title, layer.abstract)
            layer.save()
            # dates
            add_mined_dates(layer)
    except Exception as err:
        message = "update_layers_esri_imageserver: {0}".format(
            err
        )
        check = Check(
            content_object=service,
            success=False,
            response_time=0,
            message=message
        )
        check.save()


# signals

def endpointlist_post_save(instance, *args, **kwargs):
    """
    Used to process the lines of the endpoint list.
    """
    with open(instance.upload.file.name, mode='rb') as f:
        lines = f.readlines()
    for url in lines:
        if len(url) > 255:
            print 'Skipping this enpoint, as it is more than 255 characters: %s' % url
        else:
            if Endpoint.objects.filter(url=url, catalog=instance.catalog).count() == 0:
                endpoint = Endpoint(url=url, endpoint_list=instance)
                endpoint.catalog = instance.catalog
                endpoint.save()
    if not settings.REGISTRY_SKIP_CELERY:
        update_endpoints.delay(instance)
    else:
        update_endpoints(instance)


def endpoint_post_save(instance, *args, **kwargs):

    if Endpoint.objects.filter(url=instance.url).count() == 0:
        signals.post_save.disconnect(endpoint_post_save, sender=Endpoint)
        endpoint = Endpoint(url=instance.url)
        endpoint.save()
        signals.post_save.connect(endpoint_post_save, sender=Endpoint)
    if not settings.REGISTRY_SKIP_CELERY:
        update_endpoint.delay(instance)
    else:
        update_endpoint(instance)


def service_pre_save(instance, *args, **kwargs):
    """
    Used to do a service full check when saving it.
    """
    # check if service is unique
    # we cannot use unique_together as it relies on a combination of fields
    # from different models (service, resource)
    if Service.objects.filter(url=instance.url,
                              type=instance.type,
                              catalog=instance.catalog).count() > 0:
        raise Exception("There is already such a service. url={0} catalog={1}".format(
            instance.url, instance.catalog
        ))


def service_post_save(instance, *args, **kwargs):
    """
    Used to do a service full check when saving it.
    """
    # check service
    if not settings.REGISTRY_SKIP_CELERY:
        check_service.delay(instance)
    else:
        check_service(instance)


def layer_post_save(instance, *args, **kwargs):
    """
    Used to do a layer full check when saving it.
    """

    if instance.is_monitored:  # index and monitor
        if not settings.SKIP_CELERY_TASK:
            check_layer.delay(instance)
        else:
            check_layer(instance)
    else:  # just index
        check_layer(instance)


signals.post_save.connect(endpoint_post_save, sender=Endpoint)
signals.post_save.connect(endpointlist_post_save, sender=EndpointList)
signals.pre_save.connect(service_pre_save, sender=Service)
signals.post_save.connect(service_post_save, sender=Service)
signals.post_save.connect(layer_post_save, sender=Layer)
