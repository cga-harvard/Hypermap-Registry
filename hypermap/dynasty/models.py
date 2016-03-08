from django.db import models


class Dynasty(models.Model):
    """
    Dynasty represents different date periods and dynasties to check when mining
    """
    date_range = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.name
