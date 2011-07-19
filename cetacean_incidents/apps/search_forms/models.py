from django.db import models
from django import forms
from django.utils.text import capfirst

from fields import (
    AutoFieldQuery,
    BooleanFieldQuery,
    CharFieldQuery,
    DateFieldQuery,
    NullBooleanFieldQuery,
    NumberFieldQuery,
    QueryField,
)
from related import HideableManyToManyFieldQuery

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
    }
    
    defaults.update(kwargs)
    return form_class(self, **defaults)

@_searchformfield_method(models.fields.AutoField)
def autofield(self, **kwargs):
    return super(models.fields.AutoField, self).searchformfield(AutoFieldQuery, **kwargs)

@_searchformfield_method(models.fields.BooleanField)
def autofield(self, **kwargs):
    return super(models.fields.BooleanField, self).searchformfield(BooleanFieldQuery, **kwargs)

@_searchformfield_method(models.fields.CharField)
def charfield(self, **kwargs):
    return super(models.fields.CharField, self).searchformfield(CharFieldQuery, **kwargs)

@_searchformfield_method(models.fields.DateField)
def datefield(self, **kwargs):
    return super(models.fields.DateField, self).searchformfield(DateFieldQuery, **kwargs)

@_searchformfield_method(models.fields.DecimalField)
def integerfield(self, **kwargs):
    return super(models.fields.DecimalField, self).searchformfield(NumberFieldQuery, **kwargs)

@_searchformfield_method(models.fields.FloatField)
def integerfield(self, **kwargs):
    return super(models.fields.FloatField, self).searchformfield(NumberFieldQuery, **kwargs)

@_searchformfield_method(models.fields.IntegerField)
def integerfield(self, **kwargs):
    return super(models.fields.IntegerField, self).searchformfield(NumberFieldQuery, **kwargs)

@_searchformfield_method(models.fields.NullBooleanField)
def autofield(self, **kwargs):
    return super(models.fields.NullBooleanField, self).searchformfield(NullBooleanFieldQuery, **kwargs)

@_searchformfield_method(models.fields.TextField)
def charfield(self, **kwargs):
    return super(models.fields.TextField, self).searchformfield(CharFieldQuery, **kwargs)

@_searchformfield_method(models.fields.related.OneToOneField)
def onetoone(self, **kwargs):
    if self.rel and self.rel.parent_link:
        # this was created as part of multi-table inheritance
        return None
    #raise NotImplementedError
    return None

@_searchformfield_method(models.fields.related.ForeignKey)
def foreignkey(self, **kwargs):
    #raise NotImplementedError
    return None

@_searchformfield_method(models.fields.related.ManyToManyField)
def manytomany(self, **kwargs):
    return None
    #return super(models.fields.related.ManyToManyField, self).searchformfield(HideableManyToManyFieldQuery, **kwargs)

