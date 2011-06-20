from django.db import models
from django import forms
from django.utils.text import capfirst

from cetacean_incidents.apps.utils.forms import InlineRadioFieldRenderer

from fields import QueryField

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
    
    # TODO pass any relevant args from kwargs to the value_fields
    
    defaults = {
        'required': False,
        'label': capfirst(self.verbose_name),
        'help_text': self.help_text,
        'lookup_choices': (
            ('', '<anything>'),
            ('isnull', 'is blank'),
        ),
        'value_fields': {
            '': forms.CharField(widget=forms.HiddenInput(attrs={'disabled': 'disabled'})),
            'isnull': IsnullValueField(),
        },
    }
    
    if self.choices:
        # Fields with choices get special treatment
        choice_kwargs = {
            'choices': self.get_choices(include_blank=True),
            'coerce': self.to_python,
        }
        if self.null:
            choice_kwargs['empty_value'] = None
        defaults['value_fields'].update({
            'exact': forms.TypedChoiceField(**choice_kwargs),
        })
        if self.null:
            defaults['empty_value'] = None
    
    defaults.update(kwargs)
    return form_class(**defaults)

@_searchformfield_method(models.fields.AutoField)
def autofield(self, **kwargs):
    return super(models.fields.AutoField, self).searchformfield(
        lookup_choices= (
            ('', '<anything>'),
            ('exact', 'is'),
        ),
        value_fields= {
            '': forms.CharField(widget=forms.HiddenInput),
            'exact': forms.IntegerField(),
        },
    )

@_searchformfield_method(models.fields.CharField)
def charfield(self, **kwargs):
    return super(models.fields.CharField, self).searchformfield(
        lookup_choices= (
            ('', '<anything>'),
            ('exact', 'is'),
            ('isnull', 'is blank'),
        ),
        value_fields= {
            '': forms.CharField(widget=forms.HiddenInput),
            'exact': forms.CharField(),
            'isnull': IsnullValueField(),
        },
    )

