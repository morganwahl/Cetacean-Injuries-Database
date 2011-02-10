from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.contacts.forms import ContactForm

from cetacean_incidents.apps.taxons.forms import TaxonField

from cetacean_incidents.apps.vessels.forms import VesselInfoForm

from cetacean_incidents.apps.incidents.models import Animal, Case
from cetacean_incidents.apps.incidents.forms import CaseForm

from models import Shipstrike, ShipstrikeObservation, StrikingVesselInfo

class StrikingVesselInfoForm(VesselInfoForm):
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
    
    def __init__(self, data=None, initial=None, instance=None, prefix=None, *args, **kwargs):
        # the values for captain_choice and existing_captain can be set from
        # a passed 'instance', but such values should be overrideable by the 
        # passed 'initial' argument
        if not instance is None:
            if initial is None:
                initial = {}
            if not 'captain_choice' in initial:
                if instance.captain == instance.contact and not instance.contact is None:
                    initial['captain_choice'] = 'vessel'
                elif instance.captain is not None:
                    initial['captain_choice'] = 'other'
                else:
                    initial['captain_choice'] = 'none'

            if not 'existing_captain' in initial:
                if not instance.captain is None:
                    initial['existing_captain'] = instance.captain.id

        super(StrikingVesselInfoForm, self).__init__(data, initial=initial, instance=instance, prefix=prefix, *args, **kwargs)
        
        # the ContactForm for new captain contacts
        new_captain_prefix = 'new_captain'
        if not prefix is None:
            new_captain_prefix = prefix + '-' + new_captain_prefix
        self.new_captain = ContactForm(data, prefix=new_captain_prefix)
        
    # TODO for:
    #
    # __unicode__
    # __iter__
    # as_table
    # as_ul
    # as_p
    # is_multipart
    # hidden_fields
    # visible_fields
    # 
    # should we output the corresponding results from self.new_captain as well?

    def is_valid(self):
        valid = super(StrikingVesselInfoForm, self).is_valid()
        # calling is_valid will 
        #  access self.error, which will 
        #  call self.full_clean, which will 
        #  populate self.cleaned_data if not bool(self._errors)
        if not self.errors and hasattr(self, 'cleaned_data'):
            if self.cleaned_data['captain_choice'] == 'new':
                valid = self.new_captain.is_valid()
        return valid
    
    @property
    def errors(self):
        errors = super(StrikingVesselInfoForm, self).errors
        # accessing self.errors, will 
        #  call self.full_clean, which will 
        #  populate self.cleaned_data if not bool(self._errors)
        if not errors and hasattr(self, 'cleaned_data'):
            if self.cleaned_data['captain_choice'] == 'new':
                new_captain_errors = self.new_captain.errors
                if new_captain_errors:
                    errors['new_captain'] = new_captain_errors
        return errors

    def full_clean(self):
        super(StrikingVesselInfoForm, self).full_clean()
        self.new_captain.full_clean()    

    # note that we don't need to override has_changed to handle self.new_contact
    
    def save(self, commit=True):
        svi = super(StrikingVesselInfoForm, self).save(commit=False)
        
        if self.cleaned_data['captain_choice'] == 'new':
            nc = self.new_captain.save(commit=commit)

            if commit:
                svi.captain = nc
            else:
                old_m2m = self.save_m2m
                def new_m2m(self):
                    old_m2m()
                    svi.captain = nc
                    svi.save()
                self.save_m2m = new_m2m

        if self.cleaned_data['captain_choice'] == 'vessel':
            svi.captain = svi.contact
        if self.cleaned_data['captain_choice'] == 'other':
            svi.captain = self.cleaned_data['existing_captain']
        if self.cleaned_data['captain_choice'] == 'none':
            svi.captain = None
        
        if commit:
            svi.save()
            self.save_m2m()
        
        return svi

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

