from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.vessels.forms import VesselInfoForm
from cetacean_incidents.apps.incidents.models import Animal, Case, Observation
from cetacean_incidents.apps.incidents.forms import ObservationForm, CaseForm
from cetacean_incidents.apps.jquery_ui.widgets import Datepicker
from cetacean_incidents.apps.dag.forms import DAGField

from models import Entanglement, EntanglementObservation, GearType, GearOwner

class EntanglementForm(CaseForm):
    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('gear_types')
    gear_types = DAGField(
        queryset= GearType.objects.all(),
        required= _f.blank != True,
        help_text= 'selecting a type implies the ones above it in the hierarchy',
        label= _f.verbose_name.capitalize(),
    )
    
    class Meta(CaseForm.Meta):
        model = Entanglement
        exclude = 'gear_owner_info'
        widgets = CaseForm.Meta.widgets
        widgets.update({
            'analyzed_date': Datepicker,
        })

class AddEntanglementForm(EntanglementForm):
    
    class Meta(EntanglementForm.Meta):
        exclude = ('gear_owner_info', 'animal')

class EntanglementObservationForm(ObservationForm):
    
    class Meta(ObservationForm.Meta):
        model = EntanglementObservation
        # TODO how to access superclasses attrs here?
        exclude = getattr(ObservationForm.Meta, 'exclude', tuple())
        exclude += ('gear_body_location',)

class GearOwnerForm(forms.ModelForm):
    
    date_set_known = forms.BooleanField(
        initial= False,
        required= False,
        label= 'date gear was set is known',
        help_text= "check even if just the year is known"
    )
    
    location_set_known = forms.BooleanField(
        initial= False,
        required= False,
        label= 'location gear was set is known',
        help_text= "check even if just a vague location is known",
    )
    
    date_lost_known = forms.BooleanField(
        initial= False,
        required= False,
        label= 'date gear went missing is known',
        help_text= "check even if just the year is known"
    )
    
    class Meta:
        model = GearOwner
        exclude = ('case', 'date_gear_set', 'location_gear_set', 'date_gear_missing')

