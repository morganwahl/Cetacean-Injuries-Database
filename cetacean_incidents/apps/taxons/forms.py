from django import forms
from django.template.loader import render_to_string
from models import Taxon
#from django.core.validators import EMPTY_VALUES
EMPTY_VALUES = (None, '', [], (), {})

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
        js = ('jquery/jquery-1.3.2.min.js', 'taxon_widget.js')

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

