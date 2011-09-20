import re

from django import forms
from django.db import models
from django.db.models import Q
from django.utils.datastructures import SortedDict

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker

from cetacean_incidents.apps.utils.forms import (
    InlineRadioFieldRenderer,
    InlineCheckboxSelectMultiple,
    TypedMultipleChoiceField,
    DateRangeField,
)

from widgets import (
    MatchWidget,
    HiddenMatchWidget,
)

class MatchOption(object):
    
    def __init__(self, lookup, lookup_name, value_field):
        self.lookup = lookup
        self.lookup_name = lookup_name
        self.value_field = value_field

class MatchOptions(SortedDict):
    
    def __init__(self, match_options=()):
        return super(MatchOptions, self).__init__([(o.lookup, o) for o in match_options])

    def choices(self):
        return tuple([(o.lookup, o.lookup_name) for o in self.values()])
    
    def fields(self):
        return [self.lookup_field()] + self.value_fields()
    
    def lookup_field(self):
        return forms.ChoiceField(choices=self.choices())

    def value_fields(self):
        return [o.value_field for o in self.values()]
    
    def widgets(self):
        return [self.lookup_field().widget] + [vf.widget for vf in self.value_fields()]
    
    def value_field_widgets(self):
        return [o.value_field.widget for o in self.values()]

class MatchField(forms.MultiValueField):
    '''\
    A form field class with multiple subfields. One field is the match type and
    each type has another field to supply arguments. Values are 2-tuples of the
    lookup choice and the arg for that choice.
    '''
    
    widget = MatchWidget
    hidden_widget = HiddenMatchWidget
    
    def __init__(self, match_options=MatchOptions(), *args, **kwargs):
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
        
        # TODO seperate out the args and kwargs, and pass some to value_fields,
        # some to super
        
        if not 'widget' in given:
            passed['widget'] = self.widget(match_options)
        
        fields = match_options.fields()
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
    
    def validate(self, value):
        return value
    
    def compress(self, data_list):
        # TODO should we return (None, None)
        if data_list == []:
            return None
        
        # TODO should we just return ('', '')?
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

class YesNoUnknownField(TypedMultipleChoiceField):
    def __init__(self, **kwargs):
        return super(YesNoUnknownField, self).__init__(
            choices= (
                ('yes', u'Yes'),
                ('no', u'No'),
                ('unk', u'Unknown'),
            ),
            coerce= lambda v: {
                'yes': True,
                'no': False,
                'unk': None,
            }[v],
            widget= InlineCheckboxSelectMultiple,
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
    
    default_match_options = MatchOptions([
        MatchOption('', '<anything>',
            forms.CharField(
                widget=forms.HiddenInput(attrs={'disabled': 'disabled'}),
            ),
        ),
    ])
    
    blank_option = False
    
    def __init__(self, model_field, extra_match_options=None, *args, **kwargs):
        self.model_field = model_field

        match_options = MatchOptions()
        for c in reversed(self.__class__.__mro__):
            match_options.update(getattr(c, 'default_match_options', {}))
        match_options.update(extra_match_options or {})
        
        if self.blank_option and model_field.blank:
            match_options.update(MatchOptions([
                MatchOption('isnull', 'is blank', YesNoField()),
            ]))
        
        super(QueryField, self).__init__(match_options, *args, **kwargs)
    
    def query(self, value, prefix=None):
        if value is None:
            return Q()
        lookup_type, lookup_value = value
        lookup_fieldname = self.model_field.get_attname()
        if not prefix is None:
            lookup_fieldname = prefix + '__' + lookup_fieldname
        q = Q(**{lookup_fieldname + '__' + lookup_type: lookup_value})
        return q

class AutoFieldQuery(QueryField):
    default_match_options = MatchOptions([
        MatchOption('exact', 'is',
            forms.IntegerField(),
        ),
    ])

class BooleanFieldQuery(QueryField):
    default_match_options = MatchOptions([
        MatchOption('exact', 'is',
            YesNoField(),
        ),
    ])

class CharFieldQuery(QueryField):
    
    def __init__(self, model_field, *args, **kwargs):
        
        match_options = None
        
        if model_field.choices:
            # Fields with choices get special treatment
            choice_kwargs = {
                'choices': model_field.get_choices(
                    include_blank= model_field.blank, # TODO some way to respect self.blank_choice?
                    blank_choice= [(u'', u'<blank>')],
                ),
                'coerce': model_field.to_python,
                'required': True,
            }
            if model_field.null:
                choice_kwargs['empty_value'] = None
            match_options = MatchOptions([
                MatchOption('exact', 'is',
                    forms.TypedChoiceField(**choice_kwargs),
                ),
                MatchOption('in', 'is one of',
                    TypedMultipleChoiceField(widget=InlineCheckboxSelectMultiple, **choice_kwargs),
                ),
            ])
        else:
            match_options = MatchOptions([
                MatchOption('blank', 'is blank?', YesNoField()),
                MatchOption('iexact', 'is', forms.CharField()),
                MatchOption('icontains', 'contains', forms.CharField()),
            ])

        super(CharFieldQuery, self).__init__(model_field, match_options, *args, **kwargs)

    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.get_attname()
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            # blank fields and null fields are equivalent
            blank_q = Q(
                **{lookup_fieldname + '__isnull': True}
            ) | Q(
                **{lookup_fieldname + '__iexact': ''}
            )

            if lookup_type == 'iexact' and lookup_value == u'':
                return blank_q
            
            if lookup_type == 'blank':
                if lookup_value:
                    return blank_q
                else:
                    return ~ blank_q

        return super(CharFieldQuery, self).query(value, prefix)

class DateFieldQuery(QueryField):
    default_match_options = MatchOptions([
        MatchOption('lt', 'before',
            forms.DateField(widget=Datepicker),
        ),
        MatchOption('lte', 'before or on',
            forms.DateField(widget=Datepicker),
        ),
        MatchOption('exact', 'on',
            forms.DateField(widget=Datepicker),
        ),
        MatchOption('gte', 'on or after',
            forms.DateField(widget=Datepicker),
        ),
        MatchOption('gt', 'after',
            forms.DateField(widget=Datepicker),
        ),
        MatchOption('between', 'after or on and before',
            DateRangeField(date_widget=Datepicker),
        )
    ])
    
    blank_option = True

    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.get_attname()
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            # blank fields and null fields are equivalent
            if lookup_type == 'between':
                # lookup_value is an interable of datetime.dates
                q = Q(**{
                    lookup_fieldname + '__' + 'gte': lookup_value[0],
                    lookup_fieldname + '__' + 'lt': lookup_value[1],
                })
                print unicode(q)
                return q
        return super(DateFieldQuery, self).query(value, prefix)

class NullBooleanFieldQuery(QueryField):

    default_match_options = MatchOptions([
        MatchOption('in', 'is one of',
            YesNoUnknownField(),
        ),
    ])
    
    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.get_attname()
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            # None doesn't acutally work as a value for 'in'
            if lookup_type == 'in' and None in lookup_value:
                q = super(NullBooleanFieldQuery, self).query(value, prefix=prefix)
                q |= Q(**{lookup_fieldname + '__' + 'isnull': True})
                return q

        return super(NullBooleanFieldQuery, self).query(value, prefix)

class NumberFieldQuery(QueryField):
    
    blank_option = True
    
    def __init__(self, model_field, *args, **kwargs):
        
        match_options = None
        
        if model_field.choices:
            # Fields with choices get special treatment
            choice_kwargs = {
                'choices': model_field.get_choices(
                    include_blank= model_field.blank, # TODO some way to respect self.blank_option?
                    blank_choice= [(u'', u'<blank>')],
                ),
                'coerce': model_field.to_python,
                'required': True,
            }
            if model_field.null:
                choice_kwargs['empty_value'] = None
            match_options = MatchOptions([
                MatchOption('exact', 'is',
                    forms.TypedChoiceField(**choice_kwargs),
                ),
                MatchOption('in', 'is one of',
                    TypedMultipleChoiceField(widget=InlineCheckboxSelectMultiple, **choice_kwargs),
                ),
            ])
        else:
            match_options = MatchOptions([
                MatchOption('lt', 'less than',
                    forms.IntegerField(),
                ),
                MatchOption('lte', 'less than or equal to',
                    forms.IntegerField(),
                ),
                MatchOption('exact', 'is',
                    forms.IntegerField(),
                ),
                MatchOption('gte', 'greater than',
                    forms.IntegerField(),
                ),
                MatchOption('gt', 'greater than or equal to',
                    forms.IntegerField(),
                ),
                MatchOption('range', 'in the range (inclusive)',
                    forms.CharField(
                        help_text= 'Enter two numbers. You can separate them with commas or spaces.',
                    ),
                ),
            ])

        super(NumberFieldQuery, self).__init__(model_field, match_options, *args, **kwargs)
    
    # TODO This is really a job for some sort of localized number-parser
    _range_pattern = re.compile(r'[^0-9.]*([0-9.]+)[^0-9.]+([0-9.]+)')
    
    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.get_attname()
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            if lookup_type == 'range':
                # find the two numbers
                match = self._range_pattern.search(lookup_value)
                if not match:
                    raise ValidationError("Must give two numbers.")
                nums = match.groups()
                low = min(nums)
                high = max(nums)
                q = Q(**{
                    lookup_fieldname + '__gte': low,
                    lookup_fieldname + '__lte': high,
                })
                
                return q

        return super(NumberFieldQuery, self).query(value, prefix)

