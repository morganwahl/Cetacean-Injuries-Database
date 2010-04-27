import unittest

from utils import dms_to_dec, dec_to_dms

class UtilsTestCase(unittest.TestCase):
    def testDmsToDec(self):
        self.assertEquals(dms_to_dec((True, 70, 30, 0)), -70.5)
        self.assertEquals(
            dms_to_dec((False, 32, 19, 24.04)),
            32 + (19 / 60.0) + (24.04 / (60 * 60))
        )

from forms import NiceLocationForm

class NiceLocationFormTestCase(unittest.TestCase):
    def testValidation(self):
        form = NiceLocationForm({'coordinates_lat_input': '32 19 24.04 S', 'coordinates_lng_input': '71.5 W'})
        self.assertEquals(form.is_valid(), True)
        print form.cleaned_data
