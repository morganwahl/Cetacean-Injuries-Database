'''\
Helper functions for creating Form classes from Django models and database
objects.
'''

# heavily based on django.forms.models

from django.db.models import Q
from django import forms
from django.forms.forms import BaseForm, get_declared_fields
from django.forms.models import ModelFormOptions
from django.forms.widgets import media_property
from django.utils.datastructures import SortedDict

import models # needed to add the searchformfield attribute to Django's models

class SubmitDetectingForm(forms.Form):
    '''\
    A abstract 'mix-in' form with a hidden 'submitted' field with value 'yes' if
    the form was submitted. Handy for detecting submission via GET method.
    '''
    
    submitted = forms.CharField(
        widget= forms.HiddenInput,
        initial= 'yes',
    )
    
def fields_for_model(model, fields=None, exclude=None, widgets=None, formfield_callback=None):
    """
    Returns a ``SortedDict`` containing form fields for the given model.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned fields.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned fields, even if they are listed
    in the ``fields`` argument.
    """
    
    # just like django.forms.models.fields_for_model, except editable fields
    # are included and search_formfield is used instead of the formfield
    # attribute of the model field.
    
    field_list = []
    ignored = []
    opts = model._meta
    for f in opts.fields + opts.many_to_many:
        if fields and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if widgets and f.name in widgets:
            kwargs = {'widget': widgets[f.name]}
        else:
            kwargs = {}

        if formfield_callback is None:
            formfield = f.searchformfield(**kwargs)
        elif not callable(formfield_callback):
            raise TypeError('formfield_callback must be a function or callable')
        else:
            formfield = formfield_callback(f, **kwargs)

        if formfield:
            field_list.append((f.name, formfield))
        else:
            ignored.append(f.name)
    field_dict = SortedDict(field_list)
    if fields:
        field_dict = SortedDict(
            [(f, field_dict.get(f)) for f in fields
                if ((not exclude) or (exclude and f not in exclude)) and (f not in ignored)]
        )
    return field_dict

class SearchFormMetaclass(type):
    # based on ModelFormMetaclass
    def __new__(cls, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback', None)

        try:
            parents = [b for b in bases if issubclass(b, SearchForm)]
        except NameError:
            # We are defining SearchForm itself.
            parents = None
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super(SearchFormMetaclass, cls).__new__(cls, name, bases, attrs)
        if not parents:
            return new_class
        
        if 'media' not in attrs:
            new_class.media = media_property(new_class)
        opts = new_class._meta = ModelFormOptions(getattr(new_class, 'Meta', None))
        if opts.model:
            # If a model is defined, extract form fields from it.
            fields = fields_for_model(opts.model, opts.fields, opts.exclude, opts.widgets, formfield_callback)
            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class

class BaseSearchForm(BaseForm):
    # based on BaseModelForm, except without the 'instance' or 'object_data'
    
    def __init__(self, *args, **kwargs):
        opts = self._meta
        if opts.model is None:
            raise ValueError("SearchForm has no model class specified.")
        self.manager = opts.model.objects
        super(BaseSearchForm, self).__init__(*args, **kwargs)
    
    def _query(self, prefix=None):
        q = Q()
        for fieldname, field in self.fields.items():
            if not hasattr(field, 'query'):
                continue
            q &= field.query(self.cleaned_data[fieldname], prefix)
        from pprint import pprint
        pprint(unicode(q))
        return q

    def results(self):
        return self.manager.filter(self._query())
    
class SearchForm(BaseSearchForm):
    '''\
    Like a ModelForm, but different. Has a field for each field on a model, and
    bound instances have a results() method (instead of a save() method) that
    returns a queryset of model instances that match the form's data.
    '''
    
    __metaclass__ = SearchFormMetaclass
