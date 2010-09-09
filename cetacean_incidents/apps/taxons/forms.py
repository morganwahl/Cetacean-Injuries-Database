from django import forms
from django.template.loader import render_to_string
from django.core.validators import EMPTY_VALUES
from django.conf import settings

from cetacean_incidents.apps.jquery_ui.widgets import ModelAutocomplete

from models import Taxon

class TaxonWidget(forms.widgets.Widget):
    '''\
    A widget that searches Taxons while you type and allows you to select one
    of them.
    '''
    
    input_type = 'hidden'
    
    def render(self, name, value, attrs=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        
        none_display_name = 'none chosen'
        
        if value in EMPTY_VALUES:
            value = ''
            taxon_value = None
            initial_display_name = none_display_name
        else:
            try:
                taxon_value = Taxon.objects.get(id=value)
                value = unicode(taxon_value.id)
                initial_display_name = unicode(taxon_value)
            except Taxon.DoesNotExist:
                value = ''
                taxon_value = None
                initial_display_name = none_display_name
                print "No good value: %s" % repr(value)
        
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name, value=value)
        
        # assumes the the django.template.loaders.app_directories.load_template_source 
        # is being used, which is the default.
        return render_to_string('taxon_widget.html', {
            'none_display_name': none_display_name,
            'initial_display_name': initial_display_name,
            'final_attrs': forms.util.flatatt(final_attrs),
            'name': name,
        })
    
    class Media:
        css = {'all': ('taxon_widget.css',)}
        js = (settings.JQUERY_FILE, 'taxon_widget.js')

class TaxonAutocomplete(ModelAutocomplete):
    
    model = Taxon
    
    def __init__(self, attrs=None):
        super(TaxonAutocomplete, self).__init__(
            attrs=attrs,
            source= 'taxon_autocomplete_source',
            options= {
                'minLength': 2,
            },
        )
    
    def render(self, name, value, attrs=None, custom_html= None):
        return super(TaxonAutocomplete, self).render(
            name=name,
            value=value,
            attrs=attrs,
            custom_html= 'taxon_autocomplete_entry',
        )
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE, 'taxon_autocomplete.css')}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'taxon_autocomplete.js')

class TaxonField(forms.Field):
    # based on ModelChoiceField, except you can't choose queryset, and there
    # are no choices, since we're using an AJAX-y TaxonWidget
    
    # a Field's widget defaults to self.widget
    widget = TaxonWidget
    
    def clean(self, value):
        '''Value is a taxon ID as (as a string), returns a Taxon instance.'''
        
        super(TaxonField, self).clean(value)
        if value in EMPTY_VALUES:
            return None
        try:
            value = Taxon.objects.get(pk=value)
        except Taxon.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return value

