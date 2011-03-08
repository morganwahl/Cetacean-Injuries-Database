from decimal import Decimal as D

from django.test import TestCase

from utils import (
    dms_to_dec,
    dec_to_dms,
)

class UtilsTestCase(TestCase):
    def testDmsToDec(self):
        self.assertEquals(dms_to_dec((True, 70, 30, 0)), D('-70.5'))
        self.assertEquals(
            # only test to millionth of a degree
            dms_to_dec((False, 32, 19, 24.04)).quantize(D('0.000001')),
            (D('32') + (D('19') / 60) + (D('24.04') / (60 * 60))).quantize(D('0.000001'))
        )

from models import Location

from forms import NiceLocationForm

class NiceLocationFormTestCase(TestCase):
    def testValidation(self):
        form = NiceLocationForm({
            'coordinates_lat_input': '32 19 24.04 N',
            'coordinates_lng_input': '71.5 W',
            'waters': Location._meta.get_field('waters').default,
        })
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(
            form.cleaned_data['coordinates_lat_input'],
            # TODO how do we deal with rounding errors? or should the test not
            # pass if they make a difference?
            (False, D(32), D(19), D('24.04'))
        )
        self.assertEquals(
            form.cleaned_data['coordinates_lng_input'],
            (True, D('71.5'), D(0), D(0))
        )
        form = NiceLocationForm({
            'coordinates_lat_input': '32 19 24.04',
            'coordinates_lng_input': '-71.5 adfadbargha',
            'waters': Location._meta.get_field('waters').default,
        })
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(
            form.cleaned_data['coordinates_lat_input'],
            # TODO how do we deal with rounding errors? or should the test not
            # pass if they make a difference?
            (False, D(32), D(19), D('24.04'))
        )
        self.assertEquals(
            form.cleaned_data['coordinates_lng_input'],
            (True, D('71.5'), D(0), D(0))
        )
    
    def testSave(self):
        form = NiceLocationForm({
            'coordinates_lat_input': '32 19 24.04 N',
            'coordinates_lng_input': '-71.5',
            'waters': Location._meta.get_field('waters').default,
        })
        loc = form.save()

