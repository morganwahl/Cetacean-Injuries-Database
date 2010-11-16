import re

from django.db import models

from . import UncertainDateTime

from forms import UncertainDateTimeField as UncertainDateTimeFormField

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
    def get_sametime_q(cls, udt, field_lookup):
        '''
        Given a field lookup (e.g. 'datetime_reported'), returns
        a Q object that selects for objects there that UncertainDateTimeField
        may represent the same time as this one. In other words, each of their
        fields, if defined, are the same.
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
        elif lookup_type in ('regex',):
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

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

