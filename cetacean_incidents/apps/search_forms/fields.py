from django import forms
from django.db import models
from django.db.models import Q

from cetacean_incidents.apps.utils.forms import (
    InlineRadioFieldRenderer,
)

from widgets import (
    MatchWidget,
    HiddenMatchWidget,
)

class MatchField(forms.MultiValueField):
    '''\
    A form field class with multiple subfields. One field is the match type and
    each type has another field to supply arguments. Values are 2-tuples of the
    lookup choice and the arg for that choice.
    '''
    
    widget = MatchWidget
    hidden_widget = HiddenMatchWidget
    
    def __init__(self, lookup_choices, value_fields, *args, **kwargs):
        '''\
        Lookup_choices is Django choice tuple whose values are lookup types.
        value_fields is a dictionary of fields keyed to lookup types. The query
        value will be the value field that corresponds to the chosen lookup
        type.
        '''
        #from pprint import pprint
        pprint(('MatchField.__init__', lookup_choices, value_fields, args, kwargs))

        #defaults = {
        #    'required': True,
        #    'widget': None,
        #    'label': None,
        #    'initial': None,
        #    'help_text': None,
        #    'error_messages': None,
        #    'show_hidden_initial': False,
        #    'validators': [],
        #    'localize': False,
        #}
        args_dict = dict(zip((
            'required',
            'widget',
            'label',
            'initial',
            'help_text',
            'error_messages',
            'show_hidden_initial',
            'validators',
            'localize',
        ), args))
        given = {}
        #given.update(defaults)
        given.update(args_dict)
        given.update(kwargs)
        
        passed = dict(given)
        # TODO does this make sense? or is it more a QueryField thing?
        # MatchFields are never required
        passed['required'] = False
        
        lookup_field = forms.ChoiceField(choices=lookup_choices)

        # TODO seperate out the args and kwargs, and pass some to value_fields,
        # some to super
        
        fields = [
            lookup_field,
        ] + [value_fields[choice[0]] for choice in lookup_choices]
        if not 'widget' in given:
            lookup_widget = lookup_field.widget
            arg_widgets = dict(
                [(lookup, field.widget) for lookup, field in value_fields.items()]
            )
            passed['widget'] = self.widget(lookup_widget, arg_widgets)
        
        pprint(('MultiValueField.__init__', fields, passed))
        super(MatchField, self).__init__(fields, **passed)
    
    @property
    def lookup_field(self):
        return self.fields[0]
    
    def clean(self, value):
        # set all the value fields that don't correspond to lookup type to None
        # This ensures their validation always succeeds, since QueryFields are
        # never required.
        
        # note that value could be just about anything, and value[0] may not
        # be a string, much less a lookup type.
        try:
            lookup = value[0]
        except TypeError: # value isn't subscriptable
            lookup = None
        except IndexError: # there is no value[0]
            lookup = None
        
        # note that this may set all the other values to None if value[0] wasn't
        # one of the lookup_choices. that's OK, since value[0] will then fail
        # to validate.
        if not lookup is None:
            lookup_choices = self.lookup_field.choices
            for i, choice in enumerate(lookup_choices, start=1):
                if choice[0] != lookup:
                    value[i] = None
        
        return super(MatchField, self).clean(value)
    
    def compress(self, data_list):
        from pprint import pprint
        pprint(('compress', data_list))
        
        if data_list == []:
            return None
        
        if data_list[0] == '':
            return None
        
        lookup = data_list[0]
        lookup_choices = self.lookup_field.choices
        for i, choice in enumerate(lookup_choices, start=1):
            if choice[0] == lookup:
                return (lookup, data_list[i])
        
        raise NotImplementedError

class YesNoField(forms.TypedChoiceField):
    def __init__(self, **kwargs):
        return super(YesNoField, self).__init__(
            choices= (
                ('yes', u'Yes'),
                ('', u'No'),
            ),
            coerce= bool,
            widget= forms.RadioSelect(renderer=InlineRadioFieldRenderer),
            **kwargs
        )

# Which field lookups make sense for which database field types?
#
# Lookups can be grouped:
#
# - basic identity
#   - exact
#   - in
#   - isnull
# - order
#   - gt(e)
#   - lt(e)
#   - range
# - text
#   - iexact
#   - (i)contains
#   - (i)startswith
#   - (i)endswith
#   - search (MySQL only)
#   - (i)regex
# - date
#   - year
#   - month
#   - day
#   - week_day
#
# All fields can use the basic identity lookups. The other groups make sense
# as follows:
#
# - identity only
#   - AutoField
#   - BooleanField
#   - CommaSeparatedIntegerField
#   - EmailField
#   - FileField
#   - FileField and FieldFile
#   - FilePathField
#   - ImageField
#   - IPAddressField
#   - NullBooleanField
#   - SlugField
#   - TimeField
#   - URLField
#   - XMLField
#
# - order
#   - BigIntegerField
#   - DecimalField
#   - FloatField
#   - IntegerField
#   - PositiveIntegerField
#   - PositiveSmallIntegerField
#   - SmallIntegerField
#
# - text
#   - CharField
#   - TextField
#
# - order and date
#   - DateField 
#   - DateTimeField
#
# reference fields are special.
# - ForeignKey
# - OneToOneField
# - ManyToManyField

class QueryField(MatchField):
    '''\
    A form field class based on a model field class whose values are Q-objects
    that filter on the model field class.
    '''
    
    lookup_choices = (
        ('', '<anything>'),
        ('isnull', 'is blank'),
    )
    value_fields = {
        '': forms.CharField(widget=forms.HiddenInput(attrs={'disabled': 'disabled'})),
        'isnull': YesNoField(),
    }
    
    def __init__(self, model_field, *args, **kwargs):
        from pprint import pprint
        
        self.model_field = model_field

        if self.model_field.choices and hasattr(self, '_choices_fields'):
            # Fields with choices get special treatment
            self.value_fields.update(self._choices_fields())
    
        super(QueryField, self).__init__(self.lookup_choices, self.value_fields, *args, **kwargs)
    
    def query(self, value):
        if value is None:
            return Q()
        lookup_type, lookup_value = value
        lookup_fieldname = self.model_field.get_attname()
        q = Q(**{lookup_fieldname + '__' + lookup_type: lookup_value})
        from pprint import pprint
        pprint(('QueryField.query', unicode(q)))
        return q

class AutoFieldQuery(QueryField):
    lookup_choices = (
        ('', '<anything>'),
        ('exact', 'is'),
    )
    value_fields = {
        '': forms.CharField(widget=forms.HiddenInput),
        'exact': forms.IntegerField(),
    }


class CharFieldQuery(QueryField):
    
    lookup_choices = (
        ('', '<anything>'),
        ('exact', 'is'),
        ('isnull', 'is blank'),
        ('icontains', 'contains'),
    )
    value_fields = {
        '': forms.CharField(widget=forms.HiddenInput),
        'exact': forms.CharField(),
        'isnull': YesNoField(),
        'icontains': forms.CharField(),
    }

    def _choices_fields(self):
        choice_kwargs = {
            'choices': self.model_field.get_choices(include_blank=True),
            'coerce': self.model_field.to_python,
        }
        if self.model_field.null:
            choice_kwargs['empty_value'] = None
        return {
            'exact': forms.TypedChoiceField(**choice_kwargs),
        }
    
    def query(self, value):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.get_attname()
            
            # blank fields and null fields are equivalent
            if (lookup_type == 'isnull' and lookup_value) or (lookup_type == 'exact' and lookup_value == u''):
                q = Q(**{lookup_fieldname + '__' + 'isnull': True})
                q |= Q(**{lookup_fieldname + '__' + 'exact': ''})
                return q
            # do case-insensitive matching, even for 'exact'
            if lookup_type == 'exact':
                q = Q(**{lookup_fieldname + '__' + 'iexact': lookup_value})
                return q
        return super(CharFieldQuery, self).query(value)
