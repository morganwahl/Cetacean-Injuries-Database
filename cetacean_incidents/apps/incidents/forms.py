from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from models import Animal, Case, Observation, Entanglement, EntanglementObservation, Shipstrike, ShipstrikeObservation

from cetacean_incidents.apps.taxons.forms import TaxonField

observation_forms = {}

class AnimalForm(forms.ModelForm):
    
    class Meta:
        model = Animal

class AnimalWidget(forms.widgets.Input):
    '''\
    A widget that searches Animals while you type and allows you to select one
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
        animal_value = ''
        if not value is None:
            animal_value = Animal.objects.get(id=value)
        
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        
        return render_to_string('incidents/animal_widget.html', {
            'initial_animal': animal_value,
            'final_attrs': forms.util.flatatt(final_attrs),
        })
    
    class Media:
        css = {
            'all': ('animal_widget.css',),
        }
        js = ('animal_widget.js',)

class AnimalField(forms.IntegerField):
    
    def __init__(self, *args, **kwargs):
        if (not 'widget' in kwargs):
            kwargs['widget'] = AnimalWidget
        return super(AnimalField, self).__init__(*args, **kwargs)

class CaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class CreateCaseForm(forms.ModelForm):
    # only difference is the use of an AnimalField, which allows search of 
    # existing animals and indication of when to create a new Animal.
    
    animal = AnimalField()
    
    class Meta:
        model = Case

class EntanglementForm(forms.ModelForm):
    
    class Meta:
        model = Entanglement

class ShipstrikeForm(forms.ModelForm):
    
    class Meta:
        model = Shipstrike

class CaseTypeForm(forms.Form):
    '''\
    An form with the extra case-type field needed when creating new cases.
    '''
    
    # TODO get this info from the models.py
    type_names = (
        ('e', 'entanglement'),
        ('s', 'shipstrike'),
    )
    case_type = forms.ChoiceField(choices=type_names)
    # type_models's keys should be values of the case_type field
    type_models = {
        'e': Entanglement,
        's': Shipstrike,
    }
    type_forms = {
        'e': EntanglementForm,
        's': ShipstrikeForm,
    }
    
class MergeCaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class ObservationForm(forms.ModelForm):
    '''\
    This class merely handles commonalities between the different observation
    types.
    '''

    taxon = TaxonField()

    class Meta:
        model = Observation
        # the case for a new observation is set by the view
        exclude = ('case') 

observation_forms['Case'] = ObservationForm


class EntanglementObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = EntanglementObservation

observation_forms['Entanglement'] = EntanglementObservationForm


class ShipstrikeObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = ShipstrikeObservation

observation_forms['Shipstrike'] = ShipstrikeObservationForm

