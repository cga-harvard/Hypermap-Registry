import os
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand

from hypermap.aggregator.models import Layer


class Command(BaseCommand):
    help = ("Delete orphaned thumbnails.")

    def handle(self, *args, **options):
        thumbs_path = os.path.join(settings.MEDIA_ROOT, 'layers')
        for filename in os.listdir(thumbs_path):
            if filename.endswith(".jpg"):
                if Layer.objects.filter(thumbnail='layers/%s' % filename).count() == 0:
                    print 'Deleting orphaned thumb %s' % filename
                    fn = os.path.join(thumbs_path, filename)
                    os.remove(fn)
