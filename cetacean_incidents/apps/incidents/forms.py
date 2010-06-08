from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from models import Animal, Case, Observation

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.vessels.forms import VesselAdminForm

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

class CaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class AddCaseForm(CaseForm):
    '''\
    A CaseForm minus the Animal field, for adding a case to an existing animal.
    '''

    class Meta(CaseForm.Meta):
        exclude = ('animal',)

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
        initial= 'none',
        required= False,
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the reporter?",
        # help_text isn't really necessary; the choices are self-explanitory
    )
    new_observer = forms.ChoiceField(
        choices= (
            ('new', 'add a new contact'),
            ('other', 'use an existing contact'),
            ('reporter', 'same contact info as reporter'),
            ('none', 'no contact info for the observer'),
        ),
        initial= 'none',
        required= False,
        widget= forms.RadioSelect,
        #help_text= "create a new contact for the observer?",
        # help_text isn't really necessary; the choices are self-explanitory
    )

    class Meta:
        model = Observation
        # the case for a new observation is set by the view. The one-to-one 
        # relations shouldn't be shown.
        exclude = ('case', 'location', 'report_datetime', 'observation_datetime', 'observer_vessel') 
observation_forms['Case'] = ObservationForm

