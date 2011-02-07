from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.taxons.forms import TaxonField

from cetacean_incidents.apps.vessels.forms import VesselInfoForm, NiceVesselInfoForm

from cetacean_incidents.apps.incidents.models import Animal, Case
from cetacean_incidents.apps.incidents.forms import CaseForm

from models import Shipstrike, ShipstrikeObservation, StrikingVesselInfo

class StrikingVesselInfoForm(VesselInfoForm):
    
    class Meta:
        model= StrikingVesselInfo
    
class NiceStrikingVesselInfoForm(NiceVesselInfoForm):
    '''\
    To be used with a ContactForm on the same page for adding a new captain Contact.
    '''
    
    contact_choices = (
        ('new', 'add a new contact'),
        ('reporter', 'use the same contact as the reporter'),
        ('observer', 'use the same contact as the observer'),
        ('other', 'use an existing contact'),
        ('none', 'no contact info'),
    )

    contact_choice = forms.ChoiceField(
        choices= contact_choices,
        initial= 'none',
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the vessel's contact?",
    )

    captain_choices = (
        ('new', 'add a new contact'),
        ('reporter', 'use the same contact as the reporter'),
        ('observer', 'use the same contact as the observer'),
        ('vessel', 'use the same contact as for the vessel'),
        ('other', 'use an existing contact'),
        ('none', 'no contact info'),
    )
    
    captain_choice = forms.ChoiceField(
        choices= captain_choices,
        initial= 'none',
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the vessel's captain?",
    )
    
    # should be the same as whatever ModelForm would generate for the 'captain'
    # field, except it's not required.
    # TODO why not just have it generate field for captain? (which wouldn't
    # be required anyway)
    _f = StrikingVesselInfo._meta.get_field('captain')
    existing_captain = forms.ModelChoiceField(
        queryset= Contact.objects.all(),
        required= False,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    class Meta:
        model = StrikingVesselInfo
        exclude = ('contact', 'captain')

class ShipstrikeForm(CaseForm):
    
    class Meta(CaseForm.Meta):
        model = Shipstrike
        exclude = CaseForm.Meta.exclude

class AddShipstrikeForm(ShipstrikeForm):
    
    class Meta(ShipstrikeForm.Meta):
        exclude = ('animal',)

class ShipstrikeObservationForm(forms.ModelForm):

    striking_vessel_info = forms.BooleanField(
        required= False,
        help_text= "Is there any info about the striking vessel?"
    )

    class Meta:
        model = ShipstrikeObservation

