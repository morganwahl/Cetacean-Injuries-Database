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

class IsnullValueField(forms.TypedChoiceField):
    def __init__(self, **kwargs):
        return super(IsnullValueField, self).__init__(
            choices= (
                ('yes', u'Yes'),
                ('', u'No'),
            ),
            coerce= bool,
            widget= forms.RadioSelect(renderer=InlineRadioFieldRenderer),
            **kwargs
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
            'isnull': IsnullValueField(),
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


