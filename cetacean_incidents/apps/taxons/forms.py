from django.core.validators import EMPTY_VALUES
from django.core.urlresolvers import reverse
from django.conf import settings
from django import forms
from django.template.loader import render_to_string

from cetacean_incidents.apps.jquery_ui.widgets import ModelAutocomplete

from cetacean_incidents.apps.merge_form.forms import MergeForm

from models import Taxon

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
    
    def id_to_display(self, id):
        return self.model.objects.get(id=id).scientific_name()
    
    def id_to_html_display(self, id):
        taxon = Taxon.objects.get(id=id)
        return render_to_string('taxon_display.html', { 'taxon': taxon })

    def render(self, name, value, attrs=None):
        return super(TaxonAutocomplete, self).render(
            name=name,
            value=value,
            attrs=attrs,
            custom_html= 'taxon_autocomplete_entry',
            # TODO better was to pass this URL
            extra_js= '''\
            taxon_autocomplete_source_url = "%s";
            ''' % reverse('taxon_search'),
        )
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE, 'taxon_autocomplete.css')}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'taxon_autocomplete.js')

class TaxonField(forms.Field):
    # based on ModelChoiceField, except you can't choose queryset, and there
    # are no choices, since we're using an AJAX-y TaxonAutocomplete
    
    # a Field's widget defaults to self.widget
    widget = TaxonAutocomplete
    
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

class TaxonMergeForm(MergeForm):
    
    class Meta:
        model = Taxon
        
