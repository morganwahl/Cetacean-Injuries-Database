from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.vessels.forms import VesselAdminForm
from cetacean_incidents.apps.incidents.models import Animal, Case, Observation
from cetacean_incidents.apps.incidents.forms import ObservationForm, case_forms, observation_forms

from models import Shipstrike, ShipstrikeObservation, StrikingVesselInfo

class StrikingVesselInfoForm(VesselAdminForm):
    
    new_vesselcontact = forms.ChoiceField(
        choices= (
            ('new', 'add a new contact'),
            ('other', 'use an existing contact'),
            ('none', 'no contact info'),
        ),
        initial= 'none',
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the vessel's contact?",
    )
    
    class Meta(VesselAdminForm.Meta):
        model = StrikingVesselInfo

class ShipstrikeForm(forms.ModelForm):
    
    class Meta:
        model = Shipstrike

# TODO better way of tracking this
case_forms['Shipstrike'] = ShipstrikeForm

class ShipstrikeObservationForm(ObservationForm):

    striking_vessel_info = forms.BooleanField(
        required= False,
        help_text= "Is there any info about the striking vessel?"
    )

    class Meta(ObservationForm.Meta):
        model = ShipstrikeObservation

# TODO better way of tracking this
observation_forms['Shipstrike'] = ShipstrikeObservationForm

