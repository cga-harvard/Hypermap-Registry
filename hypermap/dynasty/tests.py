#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.test import TestCase
from hypermap.dynasty.utils import mine_date


class DateMinerTest(TestCase):

    def setUp(self):
        self.text_plain = 'mytext'
        self.text_year = '2003_Pathv5.0daynight_SST'
        self.text_ce = '1950CE title'
        self.text_bce = '11BCE abstract'
        self.text_dynasty = 'Ming regions'
        self.text_unicode = 'Carte des Etats-unis : 2010 provinces méridionales.'
        self.text_less_resource = "Garden in Front of Palace of Fine Arts<div> " \
                                  "<img src='http://www.ndl.go.jp/site_nippon/viennae/data/img/2_0006.jpg'" \
                                  "align='none'/></div>"
        self.text_bce_three = '160 BCE'
        self.text_multiple_dates = '2003_this_has two 2013'
        self.text_multiple_dates_2 = '_1981 2003_this_has three 2013'
        self.text_bc = '19BC abstract'
        self.text_exact_date = 'My birthday is 02/06/1971 in case you cannot remember'
        self.text_exact_dates = 'My birthday is 02/06/1971 in case you cannot remember' \
                                'My wife birthday is 09/30/1974 and my father was born in 1933.'

    def test_mine_date_none(self):
        self.assertIsNone(mine_date(self.text_plain))

    def test_mine_date_text(self):
        self.assertEqual(mine_date(self.text_year)[0], '2003-01-01')

    def test_year_miner_ce(self):
        self.assertEqual(mine_date(self.text_ce)[0], ['1950-01-01'])

    def test_year_miner_bc(self):
        self.assertEqual(mine_date(self.text_bc)[0], ['-0019-01-01'])

    def test_year_miner_bce_units(self):
        self.assertEqual(mine_date(self.text_bce_three)[0], ['-0160-01-01'])

    def test_year_miner_bce(self):
        self.assertEqual(mine_date(self.text_bce)[0], ['-0011-01-01'])

    def test_year_range_miner_range(self):
        self.assertEqual(mine_date(self.text_dynasty)[0], ['1368-01-01', '1644-01-01'])

    def test_unicode_errors(self):
        self.assertEqual(mine_date(self.text_unicode)[0], '2010-01-01')

    def test_mine_date_none_resource(self):
        self.assertIsNone(mine_date(self.text_less_resource))

    def test_mine_date_multipe(self):
        self.assertEqual(mine_date(self.text_multiple_dates), ['2003-01-01', '2013-01-01'])
        self.assertEqual(mine_date(self.text_multiple_dates_2), ['1981-01-01', '2003-01-01', '2013-01-01'])

    def test_exact_dates(self):
        self.assertEqual(mine_date(self.text_exact_dates), ['1971-01-01', '1974-01-01', '1933-01-01'])
