#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.test import TestCase
from dynasty.utils import mine_date
import datetime

class DateMinerTest(TestCase):

    def setUp(self):
        self.data = ['mytext', '2003_Pathv5.0daynight_SST', '1950CE title',
                     '11BCE abstract', 'Ming regions', 'Carte des Etats-unis : 2010 provinces méridionales.',
                     'Garden in Front of Palace of Fine Arts<div><img src="http://www.ndl.go.jp/site_nippon/viennae/data/img/2_0006.jpg" align="none"/></div>',
                      '60 BCE', '2003_this_has two 2013']

    def test_mine_date_none(self):
        self.assertIsNone(mine_date(self.data[0]))
 
    def test_mine_date_text(self):
        self.assertEqual(mine_date(self.data[1])[0].year, 2003)
 
    def test_year_miner_ce(self):
        self.assertEqual(mine_date(self.data[2])[0].isoformat(), '1950-01-01T00:00:00')

    def test_year_miner_bce(self):
        self.assertEqual(mine_date(self.data[7])[0], '-0059-01-01')

    def test_worldmap_date_miner_bce(self):
        self.assertEqual(mine_date(self.data[3])[0], '-0010-01-01')

    def test_worldmap_date_miner_range(self):
        self.assertEqual(mine_date(self.data[4])[0], '1368 TO 1644')

    def test_unicode_errors(self):
        self.assertEqual(mine_date(self.data[5])[0].year, 2010)

    def test_mine_date_none(self):
        self.assertIsNone(mine_date(self.data[6]))
    
    def test_mine_date_multipe(self):
        self.assertEqual(mine_date(self.data[8]), [datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2013, 1, 1, 0, 0)])
