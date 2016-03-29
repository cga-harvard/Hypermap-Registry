# -*- coding: utf-8 -*-

"""
Tests for the WorldMap Service Type.
"""

import unittest

from httmock import with_httmock
import mocks.worldmap

from aggregator.models import Service


class TestWorldMap(unittest.TestCase):

    @with_httmock(mocks.worldmap.resource_get)
    def test_create_worldmap_service(self):

        # create the service
        service = Service(
            type='WM',
        )
        service.save()
        # check url is correct
        self.assertTrue(service.url, 'http://worldmap.harvard.edu/')

        # check title is correct
        self.assertTrue(service.title, 'Harvard WorldMap')

        # check layer number
        self.assertEqual(service.layer_set.all().count(), 10)

        # check layer 0 (public)
        layer_0 = service.layer_set.all()[0]
        self.assertEqual(layer_0.name, 'geonode:River_basin_num2')
        self.assertEqual(layer_0.title, 'China River Basins')
        self.assertTrue(layer_0.is_public)
        self.assertEqual(layer_0.layerwm.temporal_extent_start, '1971-02-06')
        self.assertEqual(layer_0.layerwm.temporal_extent_end, '1974-09-30')
        self.assertEqual(layer_0.layerwm.category, 'Rivers, Streams, Lakes')
        self.assertEqual(layer_0.layerwm.username, 'matt')
        self.assertEqual(layer_0.keywords.all().count(), 4)
        self.assertEqual(layer_0.srs.all().count(), 3)
        self.assertEqual(layer_0.check_set.all().count(), 1)
        # TODO test layer_0.layerdate_set

        # check layer 1 (private)
        layer_1 = service.layer_set.all()[1]
        self.assertFalse(layer_1.is_public)

        # test that if creating the service and is already exiting it is not being duplicated
        # create the service
        def create_duplicated_service():
            duplicated_service = Service(
                type='WM',
            )
            duplicated_service.save()

        self.assertRaises(Exception, create_duplicated_service)


if __name__ == '__main__':
    unittest.main()
