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

        # test dates #1
        layer_with_many_dates = service.layer_set.get(name='geonode:layer_with_many_dates')
        # this layer has the following dates
        # in title: 1999, 1882
        # in abstract: 1632, 1661, 1992, 1338
        # from metadata: temporal_extent_start: 2011-01-24
        # from metadata: temporal_extent_end: 2015-09-30
        # check detected dates
        for date in ('1999-01-01', '1882-01-01', '1632-01-01', '1661-01-01', '1992-01-01'):
            self.assertEqual(layer_with_many_dates.layerdate_set.filter(date=date).filter(type='0').count(), 1)
        # check metadata dates
        for date in ('2011-01-24', '2015-09-30'):
            self.assertEqual(layer_with_many_dates.layerdate_set.filter(date=date).filter(type='1').count(), 1)

        # test dates #2
        layer_with_few_dates = service.layer_set.get(name='geonode:layer_with_few_dates')
        # this layer has the following dates
        # in title: 1990
        # in abstract: 1990, 1996, 2000
        # from metadata: temporal_extent_start: 1990-01-01
        # from metadata: temporal_extent_end: Date in invalid format
        # check detected dates
        for date in ('1990-01-01', '1996-01-01', '2000-01-01'):
            self.assertEqual(layer_with_few_dates.layerdate_set.filter(date=date).filter(type='0').count(), 1)
        # check metadata dates
        for date in ('1990-01-01', ):
            self.assertEqual(layer_with_few_dates.layerdate_set.filter(date=date).filter(type='1').count(), 1)

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
