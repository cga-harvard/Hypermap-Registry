# -*- coding: utf-8 -*-

"""
Tests for the WMS Service Type.
"""

import unittest

from httmock import with_httmock
import mocks.wms

from hypermap.aggregator.models import Service, Catalog


class TestWMS(unittest.TestCase):

    @with_httmock(mocks.wms.resource_get)
    def test_create_wms_service(self):
        catalog, created = Catalog.objects.get_or_create(
            name="hypermap", slug="hypermap",
            url="search_api"
        )

        # create the service
        service = Service(
            type='OGC:WMS',
            url='http://wms.example.com/ows?',
            catalog=catalog
        )
        service.save()

        # check layer number
        self.assertEqual(service.layer_set.all().count(), 9)

        # check layer 0 (public)
        layer_0 = service.layer_set.all()[0]
        self.assertEqual(layer_0.name, 'geonode:_30river_project1_1')
        self.assertEqual(layer_0.title, 'Rivers')
        self.assertTrue(layer_0.is_public)
        self.assertEqual(layer_0.keywords.all().count(), 3)
        self.assertEqual(layer_0.service.srs.all().count(), 2)
        self.assertEqual(layer_0.check_set.all().count(), 1)
        # TODO test layer_0.layerdate_set

        # test that if creating the service and is already exiting it is not being duplicated
        # create the service
        def create_duplicated_service():
            duplicated_service = Service(
                type='OGC:WMS',
                url='http://wms.example.com/ows?',
            )
            duplicated_service.save()

        self.assertRaises(Exception, create_duplicated_service)


if __name__ == '__main__':
    unittest.main()
