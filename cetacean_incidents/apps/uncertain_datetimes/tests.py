from django.test import TestCase

import django.forms

from datetime import datetime, timedelta
from models import UncertainDateTime
from forms import UncertainDateTimeField as UncertainDateTimeFormField

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

class UncertainDateTimeFormFieldTestCase(TestCase):
    def setUp(self):
        class the_form(django.forms.Form):
            f = UncertainDateTimeFormField()
            
        self.form_class = the_form
        
        self.blank_data = {
            'f_0': '',
            'f_1': '',
            'f_2': '',
            'f_3': '',
            'f_4': '',
            'f_5': '',
            'f_6': '',
        }
        self.full_data = {
            'f_0': '1982',
            'f_1': '3',
            'f_2': '20',
            'f_3': '12',
            'f_4': '38',
            'f_5': '02',
            'f_6': '0',
        }
        self.year_data = self.blank_data.copy()
        self.year_data['f_0'] = '2010'
    
    def test_full(self):
        form = self.form_class(self.full_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), '1982-03-20 12:38:02.000000')

    def test_blank(self):
        form = self.form_class(self.blank_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), '????-??-?? ??:??:??.??????')

    def test_year(self):
        form = self.form_class(self.year_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), '2010-??-?? ??:??:??.??????')
    
