import unittest

from django import forms

from fields import MatchField, MatchOptions, MatchOption
from related import SubqueryField

class MatchFieldTestCase(unittest.TestCase):
    
    class TestForm(forms.Form):
        f = MatchField(
            match_options= MatchOptions([
                MatchOption('', '<ignore>', forms.CharField(widget=forms.HiddenInput)),
                MatchOption('in', 'one of', forms.CharField()),
                MatchOption('exact', 'is', forms.CharField()),
            ]),
            label='the field',
            required= False,
            initial= ('in', 'some value'),
        )

    def setUp(self):
        pass
    
    def test_instantiation(self):
        f = self.TestForm()
        self.assertEqual(f.is_bound, False)
        self.assertEqual(f.is_valid(), False)
        
        f = self.TestForm(data={'f_0': 'egzact', 'f_1': 'yadda'})
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), False)
        
        f = self.TestForm(data={})
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], None)
        
        f = self.TestForm(data={'f_0': 'exact', 'f_3': ''})
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], ('exact', ''))

        f = self.TestForm(data={'f_0': '', 'f_1': 'blah blah'})
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], None)

        f = self.TestForm(data={'f_0': 'exact', 'f_3': 'test'})
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], ('exact', 'test'))

        f = self.TestForm(initial={'f': ('in', '1,2,3')})
        self.assertEqual(f.is_bound, False)

class SubqueryFieldTestCase(unittest.TestCase):
    
    class TestForm(forms.Form):
        superfield = SubqueryField(
            MatchFieldTestCase.TestForm,
            label= 'a superfield',
            required= True,
            initial= {
                'f': ('in', 'other val'),
            }
        )

    def setUp(self):
        pass
        
    def test_instantiation(self):
        f = self.TestForm()
        self.assertEqual(f.is_bound, False)
        
        f = self.TestForm(initial={
            'superfield': {
                'f': ('in', '1,2,3'),
            },
        })
        self.assertEqual(f.is_bound, False)

        f = self.TestForm(data={})
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['superfield'].is_bound, True)
        self.assertEqual(f.cleaned_data['superfield'].is_valid(), True)

        f = self.TestForm(data={
            'superfield-f_0': 'exact',
            'superfield-f_3': 'test',
        })
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['superfield'].is_bound, True)
        self.assertEqual(f.cleaned_data['superfield'].is_valid(), True)

        f = self.TestForm(data={
            'superfield-f_0': 'egzact',
            'superfield-f_1': 'yadda',
        })
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), False)

