from django.db import models
from aggregator.models import Service

class MapProxy(models.Model):
    service = models.ForeignKey(Service)
    config = models.FileField(upload_to='mapproxy/config', blank=True, null=True)
