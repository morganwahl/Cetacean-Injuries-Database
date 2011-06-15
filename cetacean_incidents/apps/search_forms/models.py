from django.db import models
from django import forms
from django.utils.text import capfirst

from cetacean_incidents.apps.utils.forms import InlineRadioFieldRenderer

from fields import QueryField

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

# map from model fields to form fields to search that field's values
identity_lookups = (
    ('exact', 'is'),
    ('in', 'is one of'),
    ('isnull', 'is blank'),
)

order_lookups = (
    ('gt', 'more than'),
    ('gte', 'more than or equal to'),
    ('lt', 'less than'),
    ('lte', 'less than or equal to'),
)

text_lookups = (
    ('iexact', 'is'),
    ('icontains', 'contains'),
    ('istartswith', 'starts with'),
    ('iendswith', 'ends with'),
)

date_lookups = (
    ('year', 'in year'),
    ('month', 'in month'),
    ('day', 'on day'),
)

# TODO is this kosher?
_attr_name = 'searchformfield'
def _searchformfield_method(cls):
    def _setmethod(method):
        setattr(cls, _attr_name, method)
        return method
    return _setmethod

# based on django.db.models.fields.Field.formfield, 'self' if a database field
# instance. The main differences are:
#  - required defaults to False
#  - self.default is ignored
#  - self.blank is ignored (there is always a blank choice)
@_searchformfield_method(models.fields.Field)
def field(self, form_class=QueryField, **kwargs):
    "Returns a django.forms.Field instance for searching this database Field."
    defaults = {
        'required': False,
        'label': capfirst(self.verbose_name),
        'help_text': self.help_text,
        'lookup_choices': (
            ('', '<ignore>'),
            ('exact', 'is'),
            ('isnull', 'is blank'),
        ),
        'value_fields': {
            '': forms.CharField(widget=forms.HiddenInput),
            'exact': forms.CharField(),
            'isnull': forms.TypedChoiceField(
                choices= (
                    ('yes', 'Yes'),
                    ('', 'No'),
                ),
                coerce= bool,
                widget= forms.RadioSelect(renderer=InlineRadioFieldRenderer),
            ),
        },
    }
    
    if self.choices:
        # Fields with choices get special treatment
        defaults['choices'] = self.get_choices(include_blank=True)
        defaults['coerce'] = self.to_python
        if self.null:
            defaults['empty_value'] = None
        # FIXME replace TypedChoiceField with a subclass of QueryField
        raise NotImplementedError
        form_class = forms.TypedChoiceField
        # Many of the subclass-specific formfield arguments (min_value,
        # max_value) don't apply for choice fields, so be sure to only pass the
        # values that TypedChoiceField will understand.
        for k in kwargs.keys():
            if k not in (
                'coerce',
                'empty_value',
                'choices',
                'required',
                'widget',
                'label',
                'initial',
                'help_text',
                'error_messages',
                'show_hidden_initial',
            ):
                del kwargs[k]
    
    defaults.update(kwargs)
    return form_class(**defaults)

@_searchformfield_method(models.fields.AutoField)
def autofield(self, **kwargs):
    return None

# TODO we're replicated the python inheritance mechanisms here. Can we just set
# the search_formfield functions as attributes of the model field classes?
# Is it kosher to add methods to other people's classes?
def search_formfield_dispatch(model_field_class):

    def unimplemented(self, **kwargs):
        from pprint import pprint
        pprint(('unimplemented', self, kwargs))
        
        return None
        raise NotImplementedError
    
    return {
        models.AutoField: autofield,
        models.BooleanField: unimplemented,
        models.CharField: unimplemented,
        models.CommaSeparatedIntegerField: unimplemented,
        models.DateField: unimplemented,
        models.DateTimeField: unimplemented,
        models.DecimalField: unimplemented,
        models.EmailField: unimplemented,
        models.FilePathField: unimplemented,
        models.FloatField: unimplemented,
        models.IntegerField: unimplemented,
        models.BigIntegerField: unimplemented,
        models.IPAddressField: unimplemented,
        models.NullBooleanField: unimplemented,
        models.PositiveIntegerField: unimplemented,
        models.PositiveSmallIntegerField: unimplemented,
        models.SlugField: unimplemented,
        models.SmallIntegerField: unimplemented,
        models.TextField: unimplemented,
        models.TimeField: unimplemented,
        models.URLField: unimplemented,
        models.XMLField: unimplemented,
        models.OneToOneField: unimplemented,
        models.ForeignKey: unimplemented,
        models.ManyToManyField: unimplemented,
    }[model_field_class]

