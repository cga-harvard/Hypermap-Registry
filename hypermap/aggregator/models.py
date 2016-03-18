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

from taggit.managers import TaggableManager
from dynasty.models import Dynasty
from polymorphic.models import PolymorphicModel
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
from arcrest import MapService as ArcMapService, ImageService as ArcImageService

from enums import SERVICE_TYPES, DATE_TYPES
from tasks import update_endpoints, check_service, check_layer, index_layer


class Resource(PolymorphicModel):
    """
    Resource represents basic information for a resource (service/layer).
    """
    title = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    url = models.URLField(max_length=255)
    is_public = models.BooleanField(default=True)

    def __unicode__(self):
        return '%s - %s' % (self.polymorphic_ctype.name, self.title)

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


class Service(Resource):
    """
    Service represents a remote geowebservice.
    """
    type = models.CharField(max_length=20, choices=SERVICE_TYPES)

    keywords = TaggableManager(blank=True)

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
        if self.type == 'OGC_WMS':
            update_layers_wms(self)
        elif self.type == 'OGC_WMTS':
            update_layers_wmts(self)
        elif self.type == 'ESRI_MapServer':
            update_layers_esri_mapserver(self)
        elif self.type == 'ESRI_ImageServer':
            update_layers_esri_imageserver(self)
        elif self.type == 'WM':
            update_layers_wm(self)
        elif self.type == 'WARPER':
            update_layers_warper(self)
        signals.post_save.connect(layer_post_save, sender=Layer)

    def check(self):
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
            if self.type == 'OGC_WMS':
                ows = WebMapService(self.url)
                title = ows.identification.title
            if self.type == 'OGC_WMTS':
                ows = WebMapTileService(self.url)
                title = ows.identification.title
            if self.type == 'ESRI_MapServer':
                esri = ArcMapService(self.url)
                title = esri.mapName
                if len(title) == 0:
                    title = get_esri_service_name(self.url)
            if self.type == 'ESRI_ImageServer':
                esri = ArcImageService(self.url)
                title = esri._json_struct['name']
                if len(title) == 0:
                    title = get_esri_service_name(self.url)
            if self.type == 'WM':
                urllib2.urlopen(self.url)
                title = 'Harvard WorldMap'
            if self.type == 'WARPER':
                urllib2.urlopen(self.url)
            # update title without raising a signal and recursion
            if title:
                Service.objects.filter(id=self.id).update(title=title)
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
        print 'Service checked in %s seconds, status is %s' % (response_time, success)


class SpatialReferenceSystem(models.Model):
    """
    SpatialReferenceSystem represents a spatial reference system.
    """
    code = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.code


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

    keywords = TaggableManager()

    def __unicode__(self):
        return self.name

    def update_thumbnail(self):
        print 'Generating thumbnail for layer id %s' % self.id
        format_error_message = 'This layer does not expose valid formats (png, jpeg) to generate the thumbnail'
        img = None
        if self.service.type == 'OGC_WMS':
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
        elif self.service.type == 'OGC_WMTS':

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
        elif self.service.type == 'WM':
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
        elif self.service.type == 'WARPER':
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
        elif self.service.type == 'ESRI_MapServer':
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
        elif self.service.type == 'ESRI_ImageServer':
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

    def worldmap_date_miner(self):
        try:
            year = re.search('\d{2,4} ?B?CE', str(self.title))
            if year is None and self.abstract:
                year = re.search('\d{2,4} ?B?CE', str(self.abstract))
        except UnicodeEncodeError:
            try:
                year = re.search('\d{2,4} ?B?CE', str(self.title.encode("ascii", "ignore")))
                if year is None and self.abstract:
                    year = re.search('\d{2,4} ?B?CE', str(self.abstract.encode("ascii", "ignore")))
            except:
                pass
        if year:
            # we get the year numeric as a string object
            year_str = str(int(filter(str.isdigit, year.group(0))))
            if "CE" in year.group(0):
                date = str(year_str.zfill(4))+'-01'+'-01'
            if "BCE" in year.group(0):
                date = str('-'+year_str.zfill(4))+'-01'+'-01'
            self.layerdate_set.get_or_create(date=date, type=0)
        else:
            dynasties = Dynasty.objects.values_list('name', flat=True)
            word_set = set(dynasties)
            abstract_set = set(self.abstract.split())
            title_set = set(self.title.split())
            common_set = None
            if word_set.intersection(title_set):
                common_set = word_set.intersection(title_set)
            if not common_set and word_set.intersection(abstract_set):
                common_set = word_set.intersection(abstract_set)
            if common_set:
                for item in common_set:
                    date_range = Dynasty.objects.get(name=item).date_range
                    self.layerdate_set.get_or_create(date=date_range, type=0)

    def mine_date(self):
        if self.service.type == "WM":
            self.worldmap_date_miner()
        date = None
        try:
            year = re.search('\d{4}', str(self.title))
            if year is None and self.abstract:
                year = re.search('\d{4}', str(self.abstract))
        except UnicodeEncodeError:
            try:
                year = re.search('\d{4}', str(self.title.encode("ascii", "ignore")))
                if year is None and self.abstract:
                    year = re.search('\d{4}', str(self.abstract.encode("ascii", "ignore")))
            except:
                pass
        if year:
            date = parse(str(year.group(0)+'-01'+'-01'))
            self.layerdate_set.get_or_create(date=date, type=0)
        return date

    def check(self):
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
            self.mine_date()
            if settings.SOLR_ENABLED:
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
        print 'Service checked in %s seconds, status is %s' % (response_time, success)

    def get_absolute_url(self):
        return reverse('layer_detail', args=(self.id,))


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


def service_post_save(instance, *args, **kwargs):
    """
    Used to do a service full check when saving it.
    """
    if not settings.SKIP_CELERY_TASK:
        check_service.delay(instance)
    else:
        if not settings.TESTING:  # hack until we fix tests
            check_service(instance)


def layer_post_save(instance, *args, **kwargs):
    """
    Used to do a layer full check when saving it.
    """
    if not settings.SKIP_CELERY_TASK:
        check_layer.delay(instance)
    else:
        if not settings.TESTING:  # hack until we fix tests
            check_layer(instance)


signals.post_save.connect(endpointlist_post_save, sender=EndpointList)
signals.post_save.connect(service_post_save, sender=Service)
signals.post_save.connect(layer_post_save, sender=Layer)
