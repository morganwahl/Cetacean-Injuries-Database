from django.test import TestCase

import django.forms

from observation import ObservationDateField

class ObservationDateFieldTestCase(TestCase):
    def setUp(self):
        class the_form(django.forms.Form):
            f = ObservationDateField()
            
        self.form_class = the_form
        
        self.blank_data = {
            'f_year': '',
            'f_month': '',
            'f_day': '',
            'f_time': '',
        }
        self.full_data = {
            'f_year': '1982',
            'f_month': '3',
            'f_day': '20',
            'f_time': '12:38:02.0',
        }
        self.year_data = self.blank_data.copy()
        self.year_data['f_year'] = '2010'
        self.month_data = self.blank_data.copy()
        self.month_data['f_month'] = '3'
        
        
    def test_unbound(self):
        form = self.form_class()
        form.is_valid()
    
    def test_full(self):
        form = self.form_class(self.full_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), u'1982-03-20 12:38:02.000000')

    def test_blank(self):
        form = self.form_class(self.blank_data)
        self.assertEquals(form.is_valid(), False)

    def test_year(self):
        form = self.form_class(self.year_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), u'2010-??-?? ??:??:??.??????')
    
    def test_month(self):
        form = self.form_class(self.month_data)
        self.assertEquals(form.is_valid(), False)
    
