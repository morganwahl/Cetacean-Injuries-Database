import django.forms
from django.test import TestCase

from ..models.animal import Animal

from animal import AnimalSearchForm
from case import CaseAnimalForm, CaseSearchForm
from observation import ObservationDateField

class CaseAnimalFormTestCase(TestCase):
    def test_instantiation(self):
        f = CaseAnimalForm()
        # unbound is invalid
        self.assertEqual(f.is_valid(), False)
        
        f = CaseAnimalForm(data={'animal': None})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['animal'], None)
        
        a = Animal.objects.create()
        f = CaseAnimalForm(initial={'animal': a.pk})
        self.assertEqual(f.is_valid(), False)
        
        f = CaseAnimalForm(data={'animal': a})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['animal'], a)

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
        self.assertEquals(unicode(form.cleaned_data['f']), u'2010')
    
    def test_month(self):
        form = self.form_class(self.month_data)
        self.assertEquals(form.is_valid(), False)

class AnimalSearchFormTestCase(TestCase):
    
    def setUp(self):
        pass
    
    def test_instantiation(self):
        f = AnimalSearchForm()
        f.as_p()
    
    def test_query(self):
        # /incidents/animals/search?animal_search-observations_0=on&animal_search-observations_1-datetime_observed_0=during&animal_search-observations_1-datetime_observed_3_year=2003
        data = {
            'observations_0': 'on',
            'observations_1-datetime_observed_0': 'during',
            'observations_1-datetime_observed_3_year': '2003',
        }
        f = AnimalSearchForm(data=data)
        self.assertEqual(f.is_valid(), True)
        f._query()

class CaseSearchFormTestCase(TestCase):
    
    def test_bug1(self):
        
        for testdata in ( ['unk'], ['yes'], ['unk', 'yes'] ):
            data = {
                'observations_0': 'on',
                'observations_1-indication_entanglement_0': 'in',
                'observations_1-indication_entanglement_2': testdata,
            }
            form = CaseSearchForm(data=data)

            self.assertEqual(form.is_valid(), True)
            # just check that this doesn't throw any exceptions
            form.results()

