'''\
Helper functions for creating Form classes from Django models and database
objects.
'''

# heavily based on django.forms.models

from django.conf import settings
from django.db.models import Q
from django import forms
from django.forms.forms import (
    BaseForm, 
    get_declared_fields,
    pretty_name,
)
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

def make_sortfield(field_dict, value_prefix=None, label_prefix=None, recursed=False):
    "If recursed is True, we're already in a sub-choices group."
    # add a sort_by field to choose one of the existing fields
    if not label_prefix is None:
        label_prefix += ': '
    else:
        label_prefix = ''
    
    sort_choices = []
    for fieldname, field in field_dict.items():
        label = field.label
        if label is None:
            label = pretty_name(fieldname)
        label = label_prefix + label
        if hasattr(field, 'sort_choices'):
            subchoices = field.sort_choices(
                value_prefix= value_prefix,
                label_prefix= label,
            )
            if not recursed:
                sort_choices.append(
                    (label, subchoices),
                )
            else:
                sort_choices += subchoices
            continue
        value = fieldname
        if not value_prefix is None:
            value = value_prefix + '__' + value
        sort_choices.append((value, label))

    #from pprint import pprint
    #pprint(('make_sortfield', sort_choices))
    sort_field = forms.ChoiceField(
        choices= tuple(sort_choices),
        required= False,
    )
    return sort_field

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

class SearchFormOptions(ModelFormOptions):
    def __init__(self, options=None):
        super(SearchFormOptions, self).__init__(options)
        self.sort_field = getattr(options, 'sort_field', None)

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
        opts = new_class._meta = SearchFormOptions(getattr(new_class, 'Meta', None))
        # TODO remove this? Currently BaseSearchForm.__init__ throws an error if
        # no model is defined.
        if opts.model:
            # If a model is defined, extract form fields from it.
            fields = fields_for_model(opts.model, opts.fields, opts.exclude, opts.widgets, formfield_callback)
            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
        if opts.sort_field:
            fields['sort_by'] = make_sortfield(fields)
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
    
    def _html_output(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row):
        """Slight adjustment to BaseForm's _html_output; the help text is put in a
        <span> with class 'help_text'."""
        # TODO is it kosher to override this? it's name does start with a '_'.
        help_text_html = u'<span class="help_text">%s</span>' % help_text_html
        return super(BaseSearchForm, self)._html_output(normal_row, error_row, row_ender, help_text_html, errors_on_separate_row)      
    
    def _query(self, prefix=None):
        if not hasattr(self, 'cleaned_data'):
            raise RuntimeError("called _query on a SearchForm that hasn't been validated!")
        q = Q()
        for fieldname, field in self.fields.items():
            if not hasattr(field, 'query'):
                continue
            q &= field.query(self.cleaned_data[fieldname], prefix)
        return q
    
    def results(self):
        qs = self.manager.filter(self._query())
        if self.cleaned_data['sort_by']:
            qs = qs.order_by(self.cleaned_data['sort_by'])
        return qs
    
    class Media:
        js = (settings.JQUERY_FILE, 'getstring_reducer.js', 'helptext_hider.js')
    
class SearchForm(BaseSearchForm):
    '''\
    Like a ModelForm, but different. Has a field for each field on a model, and
    bound instances have a results() method (instead of a save() method) that
    returns a queryset of model instances that match the form's data.
    '''
    
    __metaclass__ = SearchFormMetaclass
