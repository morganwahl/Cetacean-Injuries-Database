from django import forms
from models import Case, Observation, Entanglement, EntanglementObservation


observation_forms = {}

class CaseForm(forms.ModelForm):

    class Meta:
        model = Case

class ObservationForm(forms.ModelForm):

    class Meta:
        model = Observation
        # the case for a new observation is set by the view
        # tags_seen is an many-to-many relationship with an intermediary model.
        # ModelForm can't handle that.
        exclude = ('case', 'tags_seen') 

observation_forms['Case'] = ObservationForm

class CreateCaseForm(CaseForm):
    '''\
    A CaseForm with some additional fields for the case type.
    '''
    
    # TODO get this info from the model
    type_names = (
        ('e', 'entanglement'),
    )
    case_type = forms.ChoiceField(choices=type_names)
    # type_models's keys should be values of the case_type field
    type_models = {
        'e': Entanglement,
    }

class EntanglementForm(forms.ModelForm):
    
    class Meta:
        model = Entanglement

class EntanglementObservationForm(ObservationForm):

    class Meta(ObservationForm.Meta):
        model = EntanglementObservation

observation_forms['Entanglement'] = EntanglementObservationForm

