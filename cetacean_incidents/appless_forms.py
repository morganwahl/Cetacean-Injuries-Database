from django import forms
from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.entanglements.forms import EntanglementForm
from cetacean_incidents.apps.shipstrikes.models import Shipstrike
from cetacean_incidents.apps.shipstrikes.forms import ShipstrikeForm

# this goes here to avoid circular imports    
class CaseTypeForm(forms.Form):
    '''\
    An form with the extra case-type field needed when creating new cases.
    '''
    
    # TODO get this info from the apps.incidents.models
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

