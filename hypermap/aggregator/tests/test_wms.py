# -*- coding: utf-8 -*-

"""
Tests for the WMS Service Type.
"""

import unittest

from httmock import with_httmock
import mocks.wms

from hypermap.aggregator.models import Service, Catalog


class TestWMS1_1_1(unittest.TestCase):

    @with_httmock(mocks.wms.resource_get)
    def test_create_wms_service(self):
        catalog, created = Catalog.objects.get_or_create(
            name="hypermap", slug="hypermap",
            url="search_api"
        )

        # create the service
        service = Service(
            type='OGC:WMS',
            url='http://wms.example.com/ows111?',
            catalog=catalog
        )
        service.save()

        # check layer number
        self.assertEqual(service.layer_set.all().count(), 9)

        # check layer geonode:_30river_project1_1 (public)
        layer_0 = service.layer_set.get(name='geonode:_30river_project1_1')
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
                url='http://wms.example.com/ows111?',
            )
            duplicated_service.save()

        self.assertRaises(Exception, create_duplicated_service)


class TestWMS1_3_0(unittest.TestCase):

    @with_httmock(mocks.wms.resource_get)
    def test_create_wms_service(self):
        catalog, created = Catalog.objects.get_or_create(
            name="hypermap", slug="hypermap",
            url="search_api"
        )

        # create the service
        service = Service(
            type='OGC:WMS',
            url='http://wms.example.com/ows130?',
            catalog=catalog
        )
        service.save()

        # check layer number
        self.assertEqual(service.layer_set.all().count(), 3)

        # check layer nexrad-n0r-wmst (public)
        layer_0 = service.layer_set.get(name='nexrad-n0r-wmst')
        self.assertEqual(layer_0.title, 'NEXRAD BASE REFLECT')
        self.assertTrue(layer_0.is_public)
        self.assertEqual(layer_0.keywords.all().count(), 0)
        self.assertEqual(layer_0.service.srs.all().count(), 4)
        self.assertEqual(layer_0.check_set.all().count(), 1)
        # TODO test layer_0.layerdate_set

        # test that if creating the service and is already exiting it is not being duplicated
        # create the service
        def create_duplicated_service():
            duplicated_service = Service(
                type='OGC:WMS',
                url='http://wms.example.com/ows130?',
            )
            duplicated_service.save()

        self.assertRaises(Exception, create_duplicated_service)


class TestWMSInvalid(unittest.TestCase):

    @with_httmock(mocks.wms.resource_get)
    def test_create_wms_service(self):
        catalog, created = Catalog.objects.get_or_create(
            name="hypermap", slug="hypermap",
            url="search_api"
        )

        # create the service
        service = Service(
            type='OGC:WMS',
            url='http://wms.example.com/ows-invalid?',
            catalog=catalog
        )
        service.save()
        service.refresh_from_db()

        # check service is invalid
        self.assertEqual(service.is_valid, False)

        # check layers number
        self.assertEqual(service.layer_set.all().count(), 3)

        # check all layers are invalid
        for layer in service.layer_set.all():
            self.assertEqual(layer.is_valid, False)


if __name__ == '__main__':
    unittest.main()
