from django.core.exceptions import ValidationError
from django.forms.fields import Field
from django.forms.widgets import Widget
from django.forms.util import flatatt
from django.utils.safestring import mark_safe

from forms import SearchForm

class FormWidget(Widget):
    
    def __init__(self, form_class, *args, **kwargs):
        self.form_class = form_class
        super(FormWidget, self).__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs)
        out = u'<div%s>' % flatatt(final_attrs)
        if isinstance(value, self.form_class):
            out += value.as_p()
        else:
            out += self.form_class(prefix=name, initial=value).as_p()
        out += u'</div>'
        return mark_safe(out)
    
    def value_from_datadict(self, data, files, name):
        return self.form_class(prefix=name, data=data, files=files)
    
    def id_for_label(self, id_):
        return None
    
    @property
    def media(self):
        return self.form_class().media

class HiddenFormWidget(FormWidget):
    is_hidden = True

class SubqueryField(Field):
    
    widget = FormWidget
    hidden_widget = HiddenFormWidget
    default_error_messages = {
        'invalid': u'Enter a valid value below.',
    }
    
    def __init__(self, query_form_class, *args, **kwargs):
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
        
        self.query_form_class = query_form_class
        
        if not 'widget' in passed.keys():
            passed['widget'] = self.widget
        if issubclass(passed['widget'], Widget):
            passed['widget'] = passed['widget'](self.query_form_class)
        
        super(SubqueryField, self).__init__(**passed)
    
    def validate(self, value):
        if not isinstance(value, self.query_form_class):
            raise TypeError("value must be a %s instance" % self.query_form_class.__name__)
        if not value.is_valid():
            if self.required:
                raise ValidationError(self.error_messages['invalid'])
            else:
                return None
        return value

    def query(self, value):
        raise NotImplementedError

class ManyToManyFieldQuery(SubqueryField):
    
    def __init__(self, model_field, *args, **kwargs):
        other_model = model_field.rel.to

        self.model_field = model_field

        class other_model_search_form(SearchForm):
            class Meta:
                model = other_model
        return super(ManyToManyFieldQuery, self).__init__(other_model_search_form, *args, **kwargs)
    
    def query(self, value, prefix=None):
        if value is None:
            return Q()
            
        lookup_fieldname = self.model_field.get_attname()
        if not prefix is None:
            lookup_fieldname = prefix + '__' + lookup_fieldname
        
        q = value._query(prefix=lookup_fieldname)
        return q

class ReverseForeignKeyQuery(SubqueryField):
    
    def __init__(self, model_field, *args, **kwargs):
        # TODO model_field should be a ForeignKey instance
        self.model_field = model_field
        other_model = self.model_field.model
        class other_model_search_form(SearchForm):
            class Meta:
                model = other_model
        return super(ReverseForeignKeyQuery, self).__init__(other_model_search_form, *args, **kwargs)
    
    def query(self, value, prefix=None):
        if value is None:
            return Q()
            
        lookup_fieldname = self.model_field.related_query_name()
        if not prefix is None:
            lookup_fieldname = prefix + '__' + lookup_fieldname
        
        q = value._query(prefix=lookup_fieldname)
        return q

