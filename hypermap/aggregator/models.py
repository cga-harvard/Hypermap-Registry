from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg, Min, Max

from polymorphic.models import PolymorphicModel

from enums import SERVICE_TYPES


class Resource(PolymorphicModel):
    """
    Resource represents basic information for a resource (service/layer).
    """
    title = models.CharField(max_length=255, null=True, blank=True)
    abstract = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User)

    def __unicode__(self):
        return self.title

    @property
    def first_run(self):
        return self.status_set.order_by('checked_datetime')[0].checked_datetime

    @property
    def last_run(self):
        return self.status_set.order_by('-checked_datetime')[0].checked_datetime

    @property
    def average_response_time(self):
        return self.status_set.aggregate(Avg('response_time')).values()[0]

    @property
    def min_response_time(self):
        return self.status_set.aggregate(Min('response_time')).values()[0]

    @property
    def max_response_time(self):
        return self.status_set.aggregate(Max('response_time')).values()[0]

    @property
    def last_response_time(self):
        return self.status_set.order_by('-checked_datetime')[0].response_time

    @property
    def last_status(self):
        return self.status_set.order_by('-checked_datetime')[0].success

    @property
    def reliability(self):
        total_runs = self.status_set.count()
        success_runs = self.status_set.filter(success=True).count()
        return (success_runs/total_runs) * 100


class Service(Resource):
    """
    Service represents a remote geowebservice.
    """
    url = models.URLField(unique=True, db_index=True)
    type = models.CharField(max_length=10, choices=SERVICE_TYPES)

    def __unicode__(self):
        return self.title


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


class Status(models.Model):
    """
    Status represents the measurement of resource (service/layer) state.
    """
    resource = models.ForeignKey(Resource)
    checked_datetime = models.DateTimeField(auto_now=True)
    success = models.BooleanField(default=False)
    response_time = models.FloatField()
    message = models.CharField(max_length=255, default='OK')

    def __unicode__(self):
        return self.id
