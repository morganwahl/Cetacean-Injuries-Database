from django import forms
from models import Animal, Case, Observation, Entanglement, EntanglementObservation, Shipstrike, ShipstrikeObservation


observation_forms = {}

class CaseForm(forms.ModelForm):

    class Meta:
        model = Case

class ObservationForm(forms.ModelForm):

    class Meta:
        model = Observation
        # the case for a new observation is set by the view
        exclude = ('case') 

observation_forms['Case'] = ObservationForm

class CreateCaseForm(CaseForm):
    '''\
    A CaseForm with some additional fields for the case type.
    '''
    
    # TODO get this info from the model
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
class MergeCaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class ObservationForm(forms.ModelForm):

    #taxon = TaxonField()

    class Meta:
        model = Observation
        # the case for a new observation is set by the view
        exclude = ('case') 

observation_forms['Case'] = ObservationForm


class EntanglementForm(forms.ModelForm):
    
    class Meta:
        model = Entanglement

class EntanglementObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = EntanglementObservation

observation_forms['Entanglement'] = EntanglementObservationForm

class ShipstrikeForm(forms.ModelForm):
    
    class Meta:
        model = Shipstrike

class ShipstrikeObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = ShipstrikeObservation

observation_forms['Shipstrike'] = ShipstrikeObservationForm

