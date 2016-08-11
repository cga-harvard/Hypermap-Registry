# -*- coding: utf-8 -*-

"""
Tests for the WorldMap Service Type.
"""

import unittest

from httmock import with_httmock
import mocks.worldmap

from hypermap.aggregator.models import Service, Catalog
from hypermap.aggregator.enums import DATE_DETECTED, DATE_FROM_METADATA


class TestWorldMap(unittest.TestCase):

    @with_httmock(mocks.worldmap.resource_get)
    def test_create_worldmap_service(self):

        catalog, created = Catalog.objects.get_or_create(
            name="hypermap", slug="hypermap",
            url="search_api"
        )

        # create the service
        service = Service(
            type='Hypermap:WorldMap',
            url='http://worldmap.harvard.edu/',
            catalog=catalog
        )
        service.save()

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
        self.assertEqual(layer_0.service.srs.all().count(), 3)
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
            date_filtered = layer_with_many_dates.layerdate_set.filter(date=date)
            self.assertEqual(date_filtered.filter(type=DATE_DETECTED).count(), 1)
        # check metadata dates
        for date in ('2011-01-24', '2015-09-30'):
            date_filtered = layer_with_many_dates.layerdate_set.filter(date=date)
            self.assertEqual(
                             date_filtered.filter(type=DATE_FROM_METADATA).count(), 1)

        # test dates #2
        layer_with_few_dates = service.layer_set.get(name='geonode:layer_with_few_dates')
        # this layer has the following dates
        # in title: 1990
        # in abstract: 1990, 1996, 2000
        # from metadata: temporal_extent_start: 1990-01-01
        # from metadata: temporal_extent_end: Date in invalid format
        # check detected dates
        for date in ('1990-01-01', '1996-01-01', '2000-01-01'):
            self.assertEqual(layer_with_few_dates.layerdate_set.filter(date=date).filter(type=DATE_DETECTED).count(), 1)
        # check metadata dates
        for date in ('1990-01-01', ):

            date_filtered = layer_with_few_dates.layerdate_set.filter(date=date)
            self.assertEqual(date_filtered.filter(type=DATE_FROM_METADATA).count(), 1)

        # test dates #3
        layer_with_complex_dates = service.layer_set.get(name='geonode:layer_with_complex_dates')
        # this layer has the following dates
        # in abstract: 1900 BCE, 2000 BCE, Xia dynasty
        # from metadata: temporal_extent_start: -1900-01-01
        # from metadata: temporal_extent_end: -2000-01-01
        for date in ('-1900-01-01', '-2000-01-01', '-1600-01-01', '-2100-01-01'):
            date_filtered = layer_with_complex_dates.layerdate_set.filter(date=date)
            self.assertEqual(date_filtered.filter(type=DATE_DETECTED).count(), 1)
        # check metadata dates
        for date in ('-1900-01-01', '-2000-01-01', ):
            date_filtered = layer_with_complex_dates.layerdate_set.filter(date=date)
            self.assertEqual(date_filtered.filter(type=DATE_FROM_METADATA).count(), 1)

        # test dates #4
        layer_with_dates_in_abstract = service.layer_set.get(name='geonode:layer_with_dates_in_abstract')
        # this layer has the following dates
        # in abstract: 1901, 1902
        for date in ('1901-01-01', '1902-01-01'):
            self.assertEqual(
                             layer_with_dates_in_abstract.layerdate_set.filter(
                                date=date).filter(type=DATE_DETECTED).count(), 1)

        # test dates #5
        layer_with_html_tag = service.layer_set.get(name='geonode:layer_with_html_tag')
        self.assertEqual(layer_with_html_tag.layerdate_set.filter(date=date).filter(type=DATE_DETECTED).count(), 0)

        # check layer 1 (private)
        layer_1 = service.layer_set.all()[1]
        self.assertFalse(layer_1.is_public)

        # test that if creating the service and is already exiting it is not being duplicated
        # create the service
        def create_duplicated_service():
            duplicated_service = Service(
                type='Hypermap:WorldMap',
                url='http://worldmap.harvard.edu/'
            )
            duplicated_service.save()

        self.assertRaises(Exception, create_duplicated_service)


if __name__ == '__main__':
    unittest.main()
