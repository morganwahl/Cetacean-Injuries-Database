from django import forms
from django.template.loader import render_to_string
from models import Taxon

class TaxonWidget(forms.widgets.Input):
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
        
        # TODO error checks?
        taxon_value = ''
        if not value is None:
            taxon_value = Taxon.objects.get(id=value)
        
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        
        return render_to_string('taxons/taxon_widget.html', {
            'initial_taxon': taxon_value,
            'final_attrs': forms.util.flatatt(final_attrs),
        })
    
    class Media:
        css = {
            'all': ('taxon_widget.css',),
        }
        js = ('taxon_widget.js',)

class TaxonField(forms.IntegerField):
    
    def __init__(self, *args, **kwargs):
        if (not 'widget' in kwargs):
            kwargs['widget'] = TaxonWidget
        return super(TaxonField, self).__init__(*args, **kwargs)

class TestForm(forms.Form):
    taxon_field = TaxonField()

