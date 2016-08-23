# -*- coding: utf-8 -*-

"""
Tests for the WMS Service Type.
"""

import unittest

from httmock import with_httmock
import mocks.warper

from hypermap.aggregator.models import Service, Catalog


class TestWarper(unittest.TestCase):

    @with_httmock(mocks.warper.resource_get)
    def test_create_wms_service(self):
        catalog, created = Catalog.objects.get_or_create(
            name="hypermap", slug="hypermap",
            url="search_api"
        )
        # create the service
        service = Service(
            type='Hypermap:WARPER',
            url='http://warper.example.com/warper/maps',
            catalog=catalog
        )
        service.save()

        # check layer number
        self.assertEqual(service.layer_set.all().count(), 15)

        # check layer 0 (public)
        layer_0 = service.layer_set.all()[0]
        self.assertEqual(layer_0.name, '29568')
        self.assertEqual(layer_0.title, 'Plate 24: Map bounded by Myrtle Avenue')
        self.assertTrue(layer_0.is_public)
        self.assertEqual(layer_0.keywords.all().count(), 0)
        self.assertEqual(layer_0.service.srs.all().count(), 3)
        self.assertEqual(layer_0.check_set.all().count(), 1)
        self.assertEqual(layer_0.layerdate_set.all()[0].date, '1855-01-01')

        # a layer with no bbox must be stored with None coordinates
        layer_no_bbox = service.layer_set.get(name='16239')
        self.assertEqual(layer_no_bbox.bbox_x0, None)
        self.assertEqual(layer_no_bbox.bbox_y0, None)
        self.assertEqual(layer_no_bbox.bbox_x1, None)
        self.assertEqual(layer_no_bbox.bbox_y1, None)

        # test that if creating the service and is already exiting it is not being duplicated
        # create the service
        def create_duplicated_service():
            duplicated_service = Service(
                type='Hypermap:WARPER',
                url='http://warper.example.com/warper/maps',
            )
            duplicated_service.save()

        self.assertRaises(Exception, create_duplicated_service)

if __name__ == '__main__':
    unittest.main()
