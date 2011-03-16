from itertools import chain

from django.conf import settings
from django import forms
from django.forms.util import flatatt
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.countries.models import Country

class QuickSelect(forms.Select):
    '''\
    A widget with radio buttons for some choices and a select widget for the
    rest.
    '''
    
    OTHER_VALUE = 'other'
    QUICK_NAME_SUFFIX = '__quick'
    
    def __init__(self, attrs=None, choices=(), quick_choices=()):
        super(QuickSelect, self).__init__(attrs, choices)
        self.quick_choices = quick_choices
        self.quick_widget = forms.RadioSelect(
            choices= chain(self.quick_choices, ((self.OTHER_VALUE, 'other'),)),
        )
    
    def __deepcopy__(self, memo):
        obj = super(QuickSelect, self).__deepcopy__(memo)
        obj.quick_widget = self.quick_widget.__deepcopy__(memo)
        return obj
    
    def value_from_datadict(self, data, files, name):
        quick_val = data.get(name + self.QUICK_NAME_SUFFIX, None)
        if quick_val != self.OTHER_VALUE:
            return quick_val
        return super(QuickSelect, self).value_from_datadict(data, files, name)
    
    def render(self, name, value, attrs=None, choices=(), quick_choices=()):
        quick_value = self.OTHER_VALUE
        select_value = value
        if value is None:
            quick_value = None
        else:
            for option_value, option_label in chain(self.quick_choices, quick_choices):
                if option_value == value:
                    quick_value = value
                    select_value = ''
                    break
        
        quick_rendered = self.quick_widget.render(
            name= name + self.QUICK_NAME_SUFFIX,
            value= quick_value,
        )
        select_id = attrs['id'] + '__select'
        select_rendered = super(QuickSelect, self).render(
            name= name,
            value= select_value,
            attrs= {'id': select_id},
            choices= choices,
        )
        
        # assumes the loader
        # django.template.loaders.app_directories.load_template_source is being
        # used, which is the default.
        return get_template('country_widget.html').render(Context({
            'attrs': mark_safe(flatatt(attrs)),
            'radio_name': name + self.QUICK_NAME_SUFFIX,
            'other_value': self.OTHER_VALUE,
            'radio_widget': quick_rendered,
            'select_widget': select_rendered,
            'select_id': select_id,
        }))
    
    class Media:
        css = {'all': ('country_widget.css',)}
        js = (settings.JQUERY_FILE, 'radiohider.js')
        
class CountryWidget(QuickSelect):
    
    def __init__(self, attrs=None, choices=()):
        quick_isos = ('US', 'CA')
        quick_choices = forms.ModelChoiceField(
            queryset= Country.objects.filter(iso__in=quick_isos).order_by('-iso'),
            empty_label= 'unknown or none',
        ).choices
        
        super(CountryWidget, self).__init__(attrs, choices, quick_choices)
