from cetacean_incidents.apps.incidents.forms import ObservationForm, CaseForm

from models import Stranding, StrandingObservation

class StrandingForm(CaseForm):

    class Meta(CaseForm.Meta):
        model = Stranding

class AddStrandingForm(StrandingForm):
    
    class Meta(StrandingForm.Meta):
        exclude = ('animal')

class StrandingObservationForm(ObservationForm):
    
    class Meta(ObservationForm.Meta):
        model = StrandingObservation

