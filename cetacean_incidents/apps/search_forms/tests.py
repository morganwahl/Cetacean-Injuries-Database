#from pprint import pprint
import unittest

from django import forms

from fields import QueryField, identity_lookups, text_lookups

class QueryFieldTestCase(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def test_instantiation(self):
        class TestForm(forms.Form):
            f = QueryField(
                lookup_choices= (
                    ('', '<ignore>'),
                    ('in', 'one of'),
                    ('exact', 'is'),
                ),
                value_fields= {
                    '': forms.CharField(widget=forms.HiddenInput),
                    'in': forms.CharField(),
                    'exact': forms.CharField(),
                },
                label='the field',
                required= False,
                initial= ('in', 'some value'),
            )
        
        f = TestForm()
        #print f.as_p()
        
        self.assertEqual(f.is_bound, False)
        self.assertEqual(f.is_valid(), False)
        
        f = TestForm(data={'f_0': 'egzact', 'f_1': 'yadda'})
        #print f.as_p()
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), False)
        
        f = TestForm(data={})
        #print f.as_p()
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], None)
        
        f = TestForm(data={'f_0': 'exact', 'f_3': ''})
        #print f.as_p()
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], ('exact', ''))

        f = TestForm(data={'f_0': '', 'f_1': 'blah blah'})
        #print f.as_p()
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], None)

        f = TestForm(data={'f_0': 'exact', 'f_3': 'test'})
        #print f.as_p()
        self.assertEqual(f.is_bound, True)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['f'], ('exact', 'test'))

        f = TestForm(initial={'f': ('in', '1,2,3')})
        print f.media
        print f.as_p()
        self.assertEqual(f.is_bound, False)

