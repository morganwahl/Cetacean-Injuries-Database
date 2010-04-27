from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from models import Animal, Case, Observation, Entanglement, EntanglementObservation, Shipstrike, ShipstrikeObservation

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact

observation_forms = {}

class AnimalForm(forms.ModelForm):
    
    # ModelForm won't fill in all the handy args for us if we sepcify our own
    # field
    _f = Animal.determined_taxon.field
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )
    
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
        
        # assumes the the django.template.loaders.app_directories.load_template_source 
        # is being used, which is the default.
        return render_to_string('animal_widget.html', {
            'initial_animal': animal_value,
            'final_attrs': forms.util.flatatt(final_attrs),
        })
    
    class Media:
        css = {'all': ('animal_widget.css',)}
        js = ('animal_widget.js',)

class AnimalField(forms.ModelChoiceField):
    
    def __init__(self, *args, **kwargs):
        if (not 'widget' in kwargs):
            kwargs['widget'] = AnimalWidget
        return super(AnimalField, self).__init__(queryset=Animal.objects.all(),*args, **kwargs)

class CaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class AddCaseForm(CaseForm):
    '''\
    A CaseForm minus the Animal field, for adding a case to an existing animal.
    '''

    class Meta(CaseForm.Meta):
        exclude = ('animal',)

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

    # ModelForm won't fill in all the handy args for us if we sepcify our own
    # field
    _f = Observation._meta.get_field('taxon')
    taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )
    observer_on_vessel = forms.BooleanField(
        required= False,
        help_text= "Was the observer on a vessel?"
    )
    new_reporter = forms.ChoiceField(
        choices= (
            ('new', 'add a new contact'),
            ('other', 'use an existing contact'),
            ('none', 'no contact info for the reporter'),
        ),
        initial= 'other',
        widget= forms.RadioSelect,
        help_text= "create a new contact for the reporter?",
    )
    new_observer = forms.ChoiceField(
        choices= (
            ('new', 'add a new contact'),
            ('other', 'use an existing contact'),
            ('reporter', 'same contact info as reporter'),
            ('none', 'no contact info for the observer'),
        ),
        initial= 'other',
        widget= forms.RadioSelect,
        help_text= "create a new contact for the observer?",
    )

    class Meta:
        model = Observation
        # the case for a new observation is set by the view. The one-to-one 
        # relations shouldn't be shown.
        exclude = ('case', 'location', 'report_datetime', 'observation_datetime', 'observer_vessel') 
observation_forms['Case'] = ObservationForm

class EntanglementObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = EntanglementObservation

observation_forms['Entanglement'] = EntanglementObservationForm


class ShipstrikeObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = ShipstrikeObservation

observation_forms['Shipstrike'] = ShipstrikeObservationForm

