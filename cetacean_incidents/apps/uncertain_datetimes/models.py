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
    
    def to_python(self, value):
        if value is None:
            return None
        
        if isinstance(value, UncertainDateTime):
            return value
        
        if value is '':
            return UncertainDateTime()
        
        return UncertainDateTime.from_sortkey(value)
        
    def get_prep_value(self, value):
        
        if value is None:
            return None
        
        return value.sortkey()

    # django lookup types:
    # exact, iexact, contains, icontains, gt, gte, lt, lte, in, startswith,
    # istartswith, endswith, iendswith, range, year, month, day, isnull, search,
    # regex, iregex
    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return self.get_prep_value(value)
        elif lookup_type == 'in':
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

    def get_internal_type(self):
        return 'CharField'
        
    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

