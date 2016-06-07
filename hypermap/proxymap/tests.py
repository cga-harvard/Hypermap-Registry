from django.test import TestCase

from models import Service, Layer

SERVICE_NUMBER = 1
LAYER_PER_SERVICE_NUMBER = 2
TIMES_TO_CHECK = 1


class AggregatorTestCase(TestCase):

    def setUp(self):

        for s in range(0, SERVICE_NUMBER):
            service = Service(
                url='http://%s.fakeurl.com' % s,
                title='Title %s' % s,
                type='OGC:WMS',
            )
            service.save()
            for l in range(0, 20):
                layer = Layer(
                    name='Layer %s, from service %s' % (l, s),
                    bbox_x0=-179,
                    bbox_x1=179,
                    bbox_y0=-89,
                    bbox_y1=89,
                    service=service
                )
                layer.save()
                service.layer_set.add(layer)
        for c in range(0, TIMES_TO_CHECK):
            for s in range(0, SERVICE_NUMBER):
                service = Service.objects.all()[s]
                service.check_available()
                for layer in service.layer_set.all():
                    layer.check_available()

    def test_non_existing_layer():
        """
        Check a 404 is returned when there is no layer.
        """
        pass

    def test_config_for_layer():
        """
        Check a valid mapproxy configuration is returned when the layer exists.
        """
        pass
