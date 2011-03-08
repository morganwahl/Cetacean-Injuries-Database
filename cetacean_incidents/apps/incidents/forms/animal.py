from django import forms

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker
from cetacean_incidents.apps.merge_form.forms import MergeForm
from cetacean_incidents.apps.taxons.forms import TaxonField

from ..models import Animal

class AnimalForm(forms.ModelForm):
    
    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Animal._meta.get_field('determined_taxon')
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    class Meta:
        model = Animal
        widgets = {
            'determined_dead_before': Datepicker,
        }

class AnimalMergeSourceForm(forms.Form):
    
    # note that all fields are added dynamically in __init__
    
    def __init__(self, destination, *args, **kwargs):
        super(AnimalMergeSourceForm, self).__init__(*args, **kwargs)
        
        self.fields['source'] = forms.ModelChoiceField(
            queryset= Animal.objects.exclude(id=destination.id),
            label= 'other %s' % Animal._meta.verbose_name,
            required= True, # ensures an animal is selected
            initial= None,
            help_text= u"""Choose an animal to merge into this one. That animal's entry will be deleted and references to it will refer to this entry instead.""",
            error_messages= {
                'required': u"You must select an animal."
            },
        )

# TODO this is the same as the AnimalForm, just with a different superclass
class AnimalMergeForm(MergeForm):
    
    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Animal._meta.get_field('determined_taxon')
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    def save(self, commit=True):
        # concatenate import_notes
        self.destination.import_notes += self.source.import_notes
        return super(AnimalMergeForm, self).save(commit)
        
    class Meta:
        model = Animal
        widgets = {
            'determined_dead_before': Datepicker,
        }

