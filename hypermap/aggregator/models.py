import datetime
import os
import re
import json
from urlparse import urlparse

from django.db import models
from django.db.models import Avg, Min, Max
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse

from polymorphic.models import PolymorphicModel
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
from arcrest import Folder as ArcFolder, MapService as ArcMapService, ImageService as ArcImageService

from enums import SERVICE_TYPES


class Resource(PolymorphicModel):
    """
    Resource represents basic information for a resource (service/layer).
    """
    title = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return '%s - %s' % (self.polymorphic_ctype.name, self.title)

    @property
    def first_check(self):
        return self.check_set.order_by('checked_datetime')[0].checked_datetime

    @property
    def last_check(self):
        return self.check_set.order_by('-checked_datetime')[0].checked_datetime

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
        return self.check_set.order_by('-checked_datetime')[0].response_time

    @property
    def checks_count(self):
        return self.check_set.all().count()

    @property
    def reliability(self):
        total_checks = self.check_set.count()
        success_checks = self.check_set.filter(success=True).count()
        return (success_checks/float(total_checks)) * 100


class Service(Resource):
    """
    Service represents a remote geowebservice.
    """
    url = models.URLField(unique=True, db_index=True)
    type = models.CharField(max_length=10, choices=SERVICE_TYPES)

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
        if self.type == 'OGC:WMS':
            update_layers_wms(self)
        elif self.type == 'OGC:WMTS':
            update_layers_wmts(self)
        elif self.type == 'ESRI':
            update_layers_esri(self)

    def check(self):
        """
        Check for availability of a service and provide run metrics.
        """
        success = True
        start_time = datetime.datetime.utcnow()
        message = ''

        try:
            title = '%s %s' % (self.type, self.url)
            if self.type == 'OGC:WMS':
                ows = WebMapService(self.url)
            if self.type == 'OGC:WMTS':
                ows = WebMapTileService(self.url)
            if self.type == 'ESRI':
                esri = ArcFolder(self.url)
                title = esri.url
            # TODO add more service types here
            if self.type.startswith('OGC:'):
                title = ows.identification.title
            # update title
            self.title = title
            self.save()
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
        print 'Checked service %s' % self.title


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
    srs = models.ManyToManyField(SpatialReferenceSystem)
    service = models.ForeignKey(Service)

    def __unicode__(self):
        return self.name

    def update_thumbnail(self):
        img = None
        if self.service.type == 'OGC:WMS':
            ows = WebMapService(self.service.url)
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
                format='image/jpeg',  # TODO check available formats
                transparent=True
            )
        elif self.service.type == 'OGC:WMTS':
            ows = WebMapTileService(self.service.url)
            ows_layer = ows.contents[self.name]
            img = ows.gettile(
                                layer=self.name,
                                tilematrixset=ows_layer.tilematrixsets[0],
                                tilematrix='0',
                                row='0',
                                column='0',
                                format="image/jpeg"  # TODO check available formats
                            )
        elif self.service.type == 'ESRI':
            image = None
            if re.search("\/MapServer\/*(f=json)*", self.service.url):
                # This is a MapService
                try:
                    arcserver = ArcMapService(self.service.url)
                    bbox = (
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
            elif re.search("\/ImageServer\/*(f=json)*", self.service.url):
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
            else:
                raise NotImplementedError
            name = re.sub('[^\w\-_\. ]', '_', self.name)
            thumbnail_file_name = '%s.jpg' % name
            image.save(thumbnail_file_name)
            img = open(thumbnail_file_name, 'r')
            os.remove(thumbnail_file_name)

        # update thumb in model
        if img:
            thumbnail_file_name = '%s.jpg' % self.name
            upfile = SimpleUploadedFile(thumbnail_file_name, img.read(), "image/jpeg")
            self.thumbnail.save(thumbnail_file_name, upfile, True)
            print 'Thumbnail updated for layer %s' % self.name

    def check(self):
        """
        Check for availability of a service and provide run metrics.
        """
        success = True
        start_time = datetime.datetime.utcnow()
        message = ''

        try:
            self.update_thumbnail()

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
        print 'Checked layer %s' % self.name

    def get_absolute_url(self):
        return reverse('layer_detail', args=(self.id,))


def update_layers_wms(service):
    """
    Update layers for an OGC:WMS service.
    """
    wms = WebMapService(service.url)
    layer_names = list(wms.contents)
    for layer_name in layer_names:
        ows_layer = wms.contents[layer_name]
        print ows_layer.name
        # get or create layer
        layer, created = Layer.objects.get_or_create(name=ows_layer.name, service=service)
        if layer.active:
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


def update_layers_wmts(service):
    """
    Update layers for an OGC:WMTS service.
    """
    wmts = WebMapTileService(service.url)
    layer_names = list(wmts.contents)
    for layer_name in layer_names:
        ows_layer = wmts.contents[layer_name]
        print 'Updating layer %s' % ows_layer.name
        layer, created = Layer.objects.get_or_create(name=ows_layer.name, service=service)
        if layer.active:
            layer.title = ows_layer.title
            layer.abstract = ows_layer.abstract
            bbox = list(ows_layer.boundingBoxWGS84 or (-179.0, -89.0, 179.0, 89.0))
            layer.bbox_x0 = bbox[0]
            layer.bbox_y0 = bbox[1]
            layer.bbox_x1 = bbox[2]
            layer.bbox_y1 = bbox[3]
            layer.save()


def update_layers_esri(service):
    """
    Update layers for an ESRI REST service.
    """
    if re.search("\/MapServer\/*(f=json)*", service.url):
        esri_service = ArcMapService(service.url)
        for esri_layer in esri_service.layers:
            print 'Updating layer %s' % esri_layer.name
            layer, created = Layer.objects.get_or_create(name=esri_layer.id, service=service)
            if layer.active:
                layer.title = esri_layer.name
                layer.abstract = esri_service.serviceDescription
                layer.bbox_x0 = esri_layer.extent.xmin
                layer.bbox_y0 = esri_layer.extent.ymin
                layer.bbox_x1 = esri_layer.extent.xmax
                layer.bbox_y1 = esri_layer.extent.ymax
                # crsOptions
                srs = esri_layer.extent.spatialReference
                srs, created = SpatialReferenceSystem.objects.get_or_create(code=srs.wkid)
                layer.srs.add(srs)
                layer.save()
    elif re.search("\/ImageServer\/*(f=json)*", service.url):
        esri_service = ArcImageService(service.url)
        obj = json.loads(esri_service._contents)
        layer, created = Layer.objects.get_or_create(name=obj['name'], service=service)
        if layer.active:
            layer.title = obj['name']
            layer.abstract = esri_service.serviceDescription
            layer.bbox_x0 = str(obj['extent']['xmin'])
            layer.bbox_y0 = str(obj['extent']['ymin'])
            layer.bbox_x1 = str(obj['extent']['xmax'])
            layer.bbox_y1 = str(obj['extent']['ymax'])
            # crsOptions
            srs = obj['spatialReference']['wkid']
            layer.srs.add(srs)
            layer.save()


class Check(models.Model):
    """
    Check represents the measurement of resource (service/layer) state.
    """
    resource = models.ForeignKey(Resource)
    checked_datetime = models.DateTimeField(auto_now=True)
    success = models.BooleanField(default=False)
    response_time = models.FloatField()
    message = models.CharField(max_length=255, default='OK')

    def __unicode__(self):
        return 'Check %s' % self.id
