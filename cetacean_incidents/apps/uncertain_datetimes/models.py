from copy import deepcopy
from datetime import timedelta
import re

from django.db import models

from . import UncertainDateTime

from forms import UncertainDateTimeField as UncertainDateTimeFormField
from forms import UncertainDateTimeFieldQuery as UncertainDateTimeFormFieldQuery

class UncertainDateTimeField(models.Field):
    
    description = """a DateTime whose individual fields (year, month, day, etc)
    may be unknown"""
    
    __metaclass__ = models.SubfieldBase
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = UncertainDateTime.SORTKEY_MAX_LEN
        super(UncertainDateTimeField, self).__init__(*args, **kwargs)
    
    def db_type(self, connection):
                            # year month day hour minute second microsecond
        return 'char(%d)' % (    4   + 2 + 2  + 2    + 2    + 2         + 6)

    def to_python(self, value):
        if value is None:
            return None
        
        if isinstance(value, UncertainDateTime):
            return value
        
        if value == '':
            return UncertainDateTime()
        
        return UncertainDateTime.from_sortkey(value)
        
    def get_prep_value(self, value):
        
        if value is None:
            return None
        
        return value.sortkey()
    

    @classmethod
    def get_after_q(cls, udt, field_lookup):
        '''
        Given a field lookup for an UncertainDateTimeField 
        (e.g. 'datetime_reported'), returns a Q object that selects for 
        UncertainDateTimeField values that _may_ represent a time the same as
        or after this one.
        '''
        
        # if year is unknown, any time could possibly be after this one
        if udt.year is None:
            return models.Q()
        
        # fill in the min-values for each unknown field
        min_udt = UncertainDateTime.from_datetime(udt.earliest)
        after_q = models.Q(**{field_lookup + '__gte': min_udt.sortkey()})
        
        # TODO these _really_ depend on the format of uncertain datetimes in
        # the database
        
        # if passed 2001 3 28 ?:
        #      ?   *    * *  startswith ____
        #   2001   ?    * *  startswith 2001__
        #   2001   3    ? *  startswith 200103__
        #   2001   3   28 *         gte 20010328000000000000
        #   2001   3  >28 *  
        #   2001  >3    * *
        #  >2001   *    * *
        # are all potentially after it. (where ? indicates unknown, * is
        # any value, and >= is obvious)
        #
        # 2001 ? 3
        #      ?  *   *     startswith ____
        #   2001  ?   *     startswith 2001__
        #   2001  ?   ? *   startswith 2001____
        #   2001  ?   3 *   startswith 2001__03
        #   2001  1  >3            gte 20010103000000000000
        #   2001 >1   *
        #
        # 2001 6 ?
        #      ?  * *   startswith ____
        #   2001  ? *   startswith 2001__
        #   2001  6 *   startswith 200106
        #   2001 >6 *          gte 20010601000000000000
        #
        # 2001 3 20 12 ?
        #       ?  *   *   * *  startswith ____
        #    2001  ?   *   * *  startswith 2001__
        #    2001  3   ?   * *  startswith 200103__
        #    2001  3  20   ? *  startswith 20010320__
        #    2001  3  20  12 *  startswith 2001032012
        #    2001  3  20 >12 *         gte 20010320120000000000
        #    2001  3 >20   * *          
        #    2001 >3   *   * *          
        #   >2001  *   *   * *          
        #
        # 2001 ? 20 12 ?
        #      ?  *   *   * *   startswith ____
        #   2001  ?   *   * *   startswith 2001__
        #   2001  ?   ?   * *   startswith 2001____
        #   2001  ?  20   ? *   startswith 2001__20__
        #   2001  ?  20  12 *   startswith 2001__2012
        #   2001  1  20 >12 *          gte 20010120120000000000
        #   2001  1 >20   * *
        #   2001 >1   *   * *
        #  >2001  *   *   * *
        
        unk_year = deepcopy(udt)
        unk_year.year = None
        after_q |= models.Q(**{field_lookup + '__startswith': unk_year.sortkey()[0:4]})
        
        unk_month = deepcopy(udt)
        unk_month.month = None
        after_q |= models.Q(**{field_lookup + '__startswith': unk_month.sortkey()[0:6]})

        unk_day = deepcopy(udt)
        unk_day.day = None
        after_q |= models.Q(**{field_lookup + '__startswith': unk_day.sortkey()[0:8]})

        unk_hour = deepcopy(udt)
        unk_hour.hour = None
        after_q |= models.Q(**{field_lookup + '__startswith': unk_hour.sortkey()[0:10]})
        
        unk_minute = deepcopy(udt)
        unk_minute.minute = None
        after_q |= models.Q(**{field_lookup + '__startswith': unk_minute.sortkey()[0:12]})

        unk_second = deepcopy(udt)
        unk_second.second = None
        after_q |= models.Q(**{field_lookup + '__startswith': unk_second.sortkey()[0:14]})

        unk_microsecond = deepcopy(udt)
        unk_microsecond.microsecond = None
        after_q |= models.Q(**{field_lookup + '__startswith': unk_microsecond.sortkey()[0:20]})
        
        # TODO some of these will probably be redundant
        
        return after_q

    @classmethod
    def get_before_q(cls, udt, field_lookup):
        '''
        Given a field lookup for an UncertainDateTimeField 
        (e.g. 'datetime_reported'), returns a Q object that selects for 
        UncertainDateTimeField values that _may_ represent a time the same as
        or before this one.
        '''
        
        # if year is unknown, any time could possibly be before this one
        if udt.year is None:
            return models.Q()
        
        # fill in the max-values for each unknown field
        # since udt.latest returns the first point _not_ in the range of
        # possible ones in the udt, subtract one usec from it
        max_udt = UncertainDateTime.from_datetime(udt.latest - timedelta(microseconds=1))
        after_q = models.Q(**{field_lookup + '__lte': max_udt.sortkey()})
        
        # we don't need catch all the cases with unknown fields, since those
        # will be matched above
        
        return after_q

    @classmethod
    def get_sametime_q(cls, udt, field_lookup):
        '''
        Given a field lookup for an UncertainDateTimeField 
        (e.g. 'datetime_reported'), returns a Q object that selects for 
        UncertainDateTimeField values that _may_ represent the same time as this
        one. In other words, each of their fields, if defined, are the same.
        '''
        
        # TODO this assumes UncertainDateTime uses spaces to pad it's sortkey!
        regex = udt.sortkey().replace(' ', '.')
        regex = re.sub(r'(\d)', r'[\1 ]', regex)
        return models.Q(**{field_lookup + '__regex': regex})
    
    # django lookup types:
    # exact, iexact, contains, icontains, gt, gte, lt, lte, in, startswith,
    # istartswith, endswith, iendswith, range, year, month, day, isnull, search,
    # regex, iregex
    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('exact',):
            return self.get_prep_value(value)
        elif lookup_type in ('regex','lte','gte','startswith'):
            if isinstance(value, UncertainDateTime):
                return value.sortkey()
            return value
        elif lookup_type in ('in',):
            return [self.get_prep_value(v) for v in value]
        else:
            raise TypeError('Lookup type %r not supported.' % lookup_type)

    def formfield(self, **kwargs):
        "Returns a django.forms.Field instance for this database Field."
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {'form_class': UncertainDateTimeFormField}
        defaults.update(kwargs)
        return super(UncertainDateTimeField, self).formfield(**defaults)

    def searchformfield(self, **kwargs):
        return super(UncertainDateTimeField, self).searchformfield(UncertainDateTimeFormFieldQuery, **kwargs)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

