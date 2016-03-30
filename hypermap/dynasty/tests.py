#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.test import TestCase
from dynasty.utils import mine_date

class DateMinerTest(TestCase):

    def setUp(self):
        self.data = ['mytext', '2011text', '1950CE title',
                     '11BCE abstract', 'Ming regions', 'Carte des Etats-unis : 2010 provinces méridionales.']

    def test_mine_date_none(self):
        self.assertIsNone(mine_date(self.data[0]))
 
    def test_mine_date_text(self):
        self.assertEqual(mine_date(self.data[1])[0].year, 2011)
 
    def test_worldmap_date_miner_ce(self):
        self.assertEqual(mine_date(self.data[2])[1], '1950-01-01')

    def test_worldmap_date_miner_bce(self):
        self.assertEqual(mine_date(self.data[3])[0], '-0011-01-01')

    def test_worldmap_date_miner_range(self):
        self.assertEqual(mine_date(self.data[4])[0], '1368 TO 1644')

    def test_unicode_errors(self):
        self.assertEqual(mine_date(self.data[5])[0].year, 2010)
