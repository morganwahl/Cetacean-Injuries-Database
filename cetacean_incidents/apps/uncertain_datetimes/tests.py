from django.test import TestCase

from datetime import datetime, timedelta
from models import UncertainDateTime

class UncertainDateTimeTestCase(TestCase):
    def setUp(self):
        self.me = UncertainDateTime(year=1982,month=3,day=20)
        self.leapfeb = UncertainDateTime(year=2004, month=2)
        self.regfeb = UncertainDateTime(year=1900, month=2)
        self.leapday = UncertainDateTime(year=2004, month=2, day=29)

    def test_earliest(self):
        self.assertEquals(self.me.earliest, datetime(1982, 3, 20, 0, 0, 0, 0))
        self.assertEquals(self.leapfeb.earliest, datetime(2004, 2, 1, 0, 0, 0, 0))
        self.assertEquals(self.regfeb.earliest, datetime(1900, 2, 1, 0, 0, 0, 0))
        self.assertEquals(self.leapday.earliest, datetime(2004, 2, 29, 0, 0, 0, 0))

    def test_latest(self):
        self.assertEquals(self.me.latest, datetime(1982, 3, 21, 0, 0, 0, 0))
        self.assertEquals(self.leapfeb.latest, datetime(2004, 3, 1, 0, 0, 0, 0))
        self.assertEquals(self.regfeb.latest, datetime(1900, 3, 1, 0, 0, 0, 0))
        self.assertEquals(self.leapday.latest, datetime(2004, 3, 1, 0, 0, 0, 0))
    
    def test_breadth(self):
        self.assertEquals(self.me.breadth, timedelta(days=1))
        self.assertEquals(self.leapfeb.breadth, timedelta(days=29))
        self.assertEquals(self.regfeb.breadth, timedelta(days=28))
        self.assertEquals(self.leapday.breadth, timedelta(days=1))

