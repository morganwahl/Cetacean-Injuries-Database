from django.test import TestCase

from decimal import Decimal as D

from observation_extras import round_decimal, display_decimal

class ObservationExtrasTestCase(TestCase):
    def setUp(self):
        pass
    
    def test_round_decimal(self):
        self.assertEqual(round_decimal(D('0'), 1), D('0'))
        self.assertEqual(round_decimal(D('0'), 2), D('0'))
        self.assertEqual(round_decimal(D('98.6'), 1), D('100'))
        self.assertEqual(round_decimal(D('3.14156'), 4), D('3.142'))
    
    def test_display_decimal(self):
        self.assertEqual(display_decimal(D('0')), u'0')
        self.assertEqual(display_decimal(D('1.0')), u'1.0')
        self.assertEqual(display_decimal(D('3.14156000')), u'3.14156000')
        self.assertEqual(display_decimal(D('3.14156e-1')), u'.314156')
        self.assertEqual(display_decimal(D('-88')), u'\u221288')
        self.assertEqual(display_decimal(D('40e1')), u'4<u>0</u>0')

