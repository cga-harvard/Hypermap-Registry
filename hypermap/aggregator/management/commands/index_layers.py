import logging

from django.core.management.base import BaseCommand
from hypermap.aggregator.models import Layer
from hypermap.aggregator.tasks import index_layer

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        layers = Layer.objects.all()
        # layers = Layer.objects.filter(id=350)

        for layer in layers:
            index_layer(layer)
