from django.test import TestCase

from utils import dms_to_dec, dec_to_dms

class UtilsTestCase(TestCase):
    def testDmsToDec(self):
        self.assertEquals(dms_to_dec((True, 70, 30, 0)), -70.5)
        self.assertEquals(
            dms_to_dec((False, 32, 19, 24.04)),
            32 + (19 / 60.0) + (24.04 / (60 * 60))
        )

from forms import NiceLocationForm

class NiceLocationFormTestCase(TestCase):
    def testValidation(self):
        form = NiceLocationForm({'coordinates_lat_input': '32 19 24.04 N', 'coordinates_lng_input': '71.5 W'})
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(
            form.cleaned_data['coordinates_lat_input'],
            # TODO how do we deal with rounding errors? or should the test not
            # pass if they make a difference?
            (False, float(32), float(19), float(24.04))
        )
        self.assertEquals(
            form.cleaned_data['coordinates_lng_input'],
            (True, float(71.5), 0.0, 0.0)
        )
        form = NiceLocationForm({'coordinates_lat_input': '32 19 24.04', 'coordinates_lng_input': '-71.5 adfadbargha'})
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(
            form.cleaned_data['coordinates_lat_input'],
            # TODO how do we deal with rounding errors? or should the test not
            # pass if they make a difference?
            (False, float(32), float(19), float(24.04))
        )
        self.assertEquals(
            form.cleaned_data['coordinates_lng_input'],
            (True, float(71.5), 0.0, 0.0)
        )
    
    def testSave(self):
        form = NiceLocationForm({'coordinates_lat_input': '32 19 24.04 N', 'coordinates_lng_input': '-71.5'})
        loc = form.save()

