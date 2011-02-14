from datetime import datetime, timedelta, MINYEAR, MAXYEAR

from django.test import TestCase
import django.forms

from . import UncertainDateTime
from models import UncertainDateTimeField as UncertainDateTimeModelField
from forms import UncertainDateTimeField as UncertainDateTimeFormField

class UncertainDateTimeTestCase(TestCase):
    def setUp(self):
        self.blank = UncertainDateTime()
        self.just_year = UncertainDateTime(year=50)
        self.just_day = UncertainDateTime(day=5)
        self.point = UncertainDateTime(2010, 11, 12, 11, 59, 22, 707042)

        self.me = UncertainDateTime(year=1982,month=3,day=20)
        self.leapfeb = UncertainDateTime(year=2004, month=2)
        self.regfeb = UncertainDateTime(year=1900, month=2)
        self.leapday = UncertainDateTime(year=2004, month=2, day=29)

    def test_instance(self):
        # sometime
        UncertainDateTime()
        
        # BC
        self.assertRaises(OverflowError, UncertainDateTime, year=-1)
        
        # smarch
        self.assertRaises(ValueError, UncertainDateTime, month=13)
        
        UncertainDateTime(2010, 2, 28) # a non-leap year
        self.assertRaises(ValueError, UncertainDateTime, 2010, 2, 29)

        UncertainDateTime(2008, 2, 29) # a leap-year
        self.assertRaises(ValueError, UncertainDateTime, 2010, 2, 30)
    
    def test_known_fields(self):
        self.assertEquals(self.blank.known_fields, tuple())
        self.assertEquals(self.just_year.known_fields, ('year',))
        self.assertEquals(self.just_day.known_fields, ('day',))
        self.assertEquals(self.point.known_fields, ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond'))

    def test_anytime(self):
        self.assertEquals(self.blank.anytime, True)
        self.assertEquals(self.just_year.anytime, False)
        self.assertEquals(self.just_day.anytime, False)
        self.assertEquals(self.point.anytime, False)
    
    def test_earliest(self):
        self.assertEquals(self.blank.earliest, datetime(MINYEAR, 1, 1, 0, 0, 0, 0))
        self.assertEquals(self.just_year.earliest, datetime(50, 1, 1, 0, 0, 0, 0))
        self.assertEquals(self.just_day.earliest, datetime(MINYEAR, 1, 5, 0, 0, 0, 0))
        self.assertEquals(self.point.earliest, datetime(2010, 11, 12, 11, 59, 22, 707042))

        self.assertEquals(self.me.earliest, datetime(1982, 3, 20, 0, 0, 0, 0))
        self.assertEquals(self.leapfeb.earliest, datetime(2004, 2, 1, 0, 0, 0, 0))
        self.assertEquals(self.regfeb.earliest, datetime(1900, 2, 1, 0, 0, 0, 0))
        self.assertEquals(self.leapday.earliest, datetime(2004, 2, 29, 0, 0, 0, 0))

    def test_latest(self):
        self.assertEquals(self.blank.latest, datetime(MAXYEAR, 12, 31, 23, 59, 59, 999999))
        self.assertEquals(self.just_year.latest, datetime(51, 1, 1, 0, 0, 0, 0))
        self.assertEquals(self.just_day.latest, datetime(MAXYEAR, 12, 6, 0, 0, 0, 0))
        self.assertEquals(self.point.latest, datetime(2010, 11, 12, 11, 59, 22, 707043))

        self.assertEquals(self.me.latest, datetime(1982, 3, 21, 0, 0, 0, 0))
        self.assertEquals(self.leapfeb.latest, datetime(2004, 3, 1, 0, 0, 0, 0))
        self.assertEquals(self.regfeb.latest, datetime(1900, 3, 1, 0, 0, 0, 0))
        self.assertEquals(self.leapday.latest, datetime(2004, 3, 1, 0, 0, 0, 0))
    
    def test_breadth(self):
        self.assertEquals(
            self.blank.breadth, 
            # how long is forever? well, in python it's:
            datetime(MAXYEAR, 12, 31, 23, 59, 59, 999999) - datetime(MINYEAR, 1, 1, 0, 0, 0, 0)
        )
        self.assertEquals(self.just_year.breadth, timedelta(days=365)) # year 50 isn't a leap year
        self.assertEquals(
            self.just_day.breadth, 
            datetime(MAXYEAR, 12, 6, 0, 0, 0, 0) - datetime(MINYEAR, 1, 5, 0, 0, 0, 0)
        )
        self.assertEquals(self.point.breadth, timedelta(microseconds=1))

        self.assertEquals(self.me.breadth, timedelta(days=1))
        self.assertEquals(self.leapfeb.breadth, timedelta(days=29))
        self.assertEquals(self.regfeb.breadth, timedelta(days=28))
        self.assertEquals(self.leapday.breadth, timedelta(days=1))
    
    def test_unicode(self):
        unicode_reps = (
            {
                'uncertain_datetime': self.blank,
                'pairs': (
                    # kwargs, return
                    ({},                                            u'????-??-?? ??:??:??.??????'),
                    ({'unknown_char': None},                        u''),
                    ({'unknown_char': '_'},                         u'____-__-__ __:__:__.______'),
                    ({                      'seconds': False},      u'????-??-?? ??:??'),
                    ({'unknown_char': '_' , 'seconds': False},      u'____-__-__ __:__'),
                    ({                      'microseconds': False}, u'????-??-?? ??:??:??'),
                    ({'unknown_char': '_' , 'microseconds': False}, u'____-__-__ __:__:__'),
                ),
            },
            {
                'uncertain_datetime': self.just_year,
                'pairs': (
                    # kwargs, return
                    ({},                                            u'0050-??-?? ??:??:??.??????'),
                    ({'unknown_char': None},                        u'0050'),
                    ({'unknown_char': '_'},                         u'0050-__-__ __:__:__.______'),
                    ({                      'seconds': False},      u'0050-??-?? ??:??'),
                    ({'unknown_char': '_' , 'seconds': False},      u'0050-__-__ __:__'),
                    ({                      'microseconds': False}, u'0050-??-?? ??:??:??'),
                    ({'unknown_char': '_' , 'microseconds': False}, u'0050-__-__ __:__:__'),
                ),
            },
            {
                'uncertain_datetime': self.just_day,
                'pairs': (
                    # kwargs, return
                    ({},                                            u'????-??-05 ??:??:??.??????'),
                    ({'unknown_char': None},                        u''),
                    ({'unknown_char': '_'},                         u'____-__-05 __:__:__.______'),
                    ({                      'seconds': False},      u'????-??-05 ??:??'),
                    ({'unknown_char': '_' , 'seconds': False},      u'____-__-05 __:__'),
                    ({                      'microseconds': False}, u'????-??-05 ??:??:??'),
                    ({'unknown_char': '_' , 'microseconds': False}, u'____-__-05 __:__:__'),
                ),
            },
            {
                # self.point = UncertainDateTime(2010, 11, 12, 11, 59, 22, 707042)
                'uncertain_datetime': self.point,
                'pairs': (
                    # kwargs, return
                    ({},                                            u'2010-11-12 11:59:22.707042'),
                    ({'unknown_char': None},                        u'2010-11-12 11:59:22.707042'),
                    ({'unknown_char': '_'},                         u'2010-11-12 11:59:22.707042'),
                    ({                      'seconds': False},      u'2010-11-12 11:59'),
                    ({'unknown_char': '_' , 'seconds': False},      u'2010-11-12 11:59'),
                    ({                      'microseconds': False}, u'2010-11-12 11:59:22'),
                    ({'unknown_char': '_' , 'microseconds': False}, u'2010-11-12 11:59:22'),
                ),
            },
        )
        
        for rep in unicode_reps:
            dt = rep['uncertain_datetime']
            for kwargs, ret in rep['pairs']:
                self.assertEqual(dt.to_unicode(**kwargs), ret)

class UncertainDateTimeFormFieldTestCase(TestCase):
    def setUp(self):
        class the_form(django.forms.Form):
            f = UncertainDateTimeFormField()
            
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
        self.partial_time_data = {
            'f_year': '1982',
            'f_month': '3',
            'f_day': '20',
            'f_time': '12:20',
        }
        self.year_data = self.blank_data.copy()
        self.year_data['f_year'] = '2010'
    
    def test_unbound(self):
        form = self.form_class()
        form.is_valid()
    
    def test_full(self):
        form = self.form_class(self.full_data)
        self.assertEquals(form.is_valid(), True)
        dt = form.cleaned_data['f']
        self.assertEquals(unicode(dt), u'1982-03-20 12:38:02.000000')
        
        # hard to test the HTML output, but at least make sure it doesn't raise
        # an exception
        form = self.form_class(initial={'f': dt})

    def test_partial_time(self):
        form = self.form_class(self.partial_time_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), u'1982-03-20 12:20')

    def test_blank(self):
        form = self.form_class(self.blank_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), u'')

    def test_year(self):
        form = self.form_class(self.year_data)
        self.assertEquals(form.is_valid(), True)
        self.assertEquals(unicode(form.cleaned_data['f']), u'2010')
    
class UncertainDateTimeModelFieldTestCase(TestCase):

    def setUp(self):
        self.blank = UncertainDateTime()
        self.just_year = UncertainDateTime(2010)
        self.date = UncertainDateTime(2010, 3, 20)
        self.time = UncertainDateTime(None, None, None, 11, 8, 26, 384938)
        self.full = UncertainDateTime(1982, 3, 20, 12, 38, 2, 0)
        self.leap_year = UncertainDateTime(2008, 2)

    def test_after_q(self):
        # just testing for exception-throwing for now
        UncertainDateTimeModelField.get_after_q(self.blank, 'fieldname')
        UncertainDateTimeModelField.get_after_q(self.just_year, 'fieldname')
        UncertainDateTimeModelField.get_after_q(self.date, 'fieldname')
        UncertainDateTimeModelField.get_after_q(self.time, 'fieldname')
        UncertainDateTimeModelField.get_after_q(self.full, 'fieldname')
        UncertainDateTimeModelField.get_after_q(self.leap_year, 'fieldname')
    
    def test_before_q(self):
        # just testing for exception-throwing for now
        UncertainDateTimeModelField.get_before_q(self.blank, 'fieldname')
        UncertainDateTimeModelField.get_before_q(self.just_year, 'fieldname')
        UncertainDateTimeModelField.get_before_q(self.date, 'fieldname')
        UncertainDateTimeModelField.get_before_q(self.time, 'fieldname')
        UncertainDateTimeModelField.get_before_q(self.full, 'fieldname')
        UncertainDateTimeModelField.get_before_q(self.leap_year, 'fieldname')
        
