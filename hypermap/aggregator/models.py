from django.db import models
from django.contrib.auth.models import User

from polymorphic.models import PolymorphicModel

from enums import SERVICE_TYPES


class Resource(PolymorphicModel):
    """
    Resource represents basic information for a resource (service/layer).
    """
    title = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.title


class Service(Resource):
    """
    Service represents a remote geowebservice.
    """
    url = models.URLField(unique=True, db_index=True)
    abstract = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=10, choices=SERVICE_TYPES)
    owner = models.ForeignKey(User)


class Status(models.Model):
    """
    Status represents the measurement of resource (service/layer) state.
    """
    resource = models.ForeignKey(Resource)
    checked_datetime = models.DateTimeField(auto_now=True)
    success = models.BooleanField(default=False)
    response_time = models.FloatField()
    message = models.CharField(max_length=255, default='OK')
