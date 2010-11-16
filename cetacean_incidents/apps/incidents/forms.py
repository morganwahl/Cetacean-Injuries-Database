import datetime
from itertools import chain

from django import forms
from django.core.exceptions import ValidationError
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from models import Animal, Case, YearCaseNumber, Observation

from cetacean_incidents.apps.merge_form.forms import MergeForm
from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.jquery_ui.widgets import Datepicker
from cetacean_incidents.apps.uncertain_datetimes.forms import UncertainDateTimeField

class AnimalForm(forms.ModelForm):
    
    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Animal.determined_taxon.field
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    class Meta:
        model = Animal
        widgets = {
            'determined_dead_before': Datepicker,
        }

# TODO this is the same as the AnimalForm, just with a different superclass
class AnimalMergeForm(MergeForm):
    
    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Animal.determined_taxon.field
    determined_taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    class Meta:
        model = Animal
        widgets = {
            'determined_dead_before': Datepicker,
        }

class CaseForm(forms.ModelForm):
    
    class Meta:
        model = Case
        # custom widgets for date fields
        widgets = {
            'happened_after': Datepicker,
            'review_1_date': Datepicker,
            'review_2_date': Datepicker,
        }

class AddCaseForm(CaseForm):
    
    class Meta(CaseForm.Meta):
        exclude = ('animal',)

class MergeCaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class ObservationDateField(UncertainDateTimeField):
    
    def __init__(self, *args, **kwargs):
        return super(ObservationDateField, self).__init__(
            required_subfields= ('year',),
            hidden_subfields=('hour', 'minute', 'second', 'microsecond'),
        )
    
    def clean(self, value):
        dt = super(ObservationDateField, self).clean(value)
        
        if not dt.month is None:
            if dt.year is None:
                raise ValidationError("can't give month without year")
        
        if not dt.day is None:
            if dt.month is None:
                raise ValidationError("can't give day without month")
        
        if not dt.minute is None:
            if dt.hour is None:
                raise ValidationError("can't give minute without hour")
        
        if not dt.second is None:
            if dt.minute is None:
                raise ValidationError("can't give second without minute")
        
        if not dt.microsecond is None:
            if dt.second is None:
                raise ValidationError("can't give microsecond without second")

        return dt

class ObservationForm(forms.ModelForm):
    '''\
    This class merely handles commonalities between the different observation
    types. Should be accopanied by forms for Location, two Datetimes, a 
    VesselInfo, and two Contacts.
    '''

    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Observation._meta.get_field('taxon')
    taxon = TaxonField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Observation._meta.get_field('datetime_observed')
    datetime_observed = ObservationDateField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Observation._meta.get_field('datetime_reported')
    datetime_reported = ObservationDateField(
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
        exclude = ('case', 'location', 'observer_vessel')

class SubmitDetectingForm(forms.Form):
    '''\
    A form with a hidden 'submitted' field with value 'yes' if the form was
    submitted. Handy for detecting submission via GET method.
    '''
    
    submitted = forms.CharField(
        widget= forms.HiddenInput,
        initial= 'yes',
    )
    
class AnimalIDLookupForm(SubmitDetectingForm):
    local_id = forms.IntegerField(
        #help_text= u"lookup a particular case by numeric ID",
        label= "Local ID",
    )
    
    def clean_local_id(self):
        data = self.cleaned_data['local_id']
        try:
            animal = Animal.objects.get(id=data)
        except Animal.DoesNotExist:
            raise forms.ValidationError("no animal with that ID")
        return animal

class AnimalNMFSIDLookupForm(SubmitDetectingForm):
    nmfs_id = forms.CharField(
        help_text= u"look up an animal by the NMFS ID for one of its cases",
        label= "NMFS case ID",
    )
    
    def clean_nmfs_id(self):
        data = self.cleaned_data['nmfs_id']
        animals = Animal.objects.filter(case__nmfs_id__iexact=data)
        # nmfs_id isn't garanteed to be unique
        if animals.count() < 1:
            raise forms.ValidationError("no case has been marked as corresponding to that NMFS case")
        elif animals.count() > 1:
            animal_ids = animals.values_list('id', flat=True).order_by('id')
            raise forms.ValidationError("Multiple animals have cases that correspond to that NMFS case. Their local-IDs are: %s" % ', '.join(map(unicode, animal_ids)))
        return animals[0]

class CaseIDLookupForm(SubmitDetectingForm):
    local_id = forms.IntegerField(
        #help_text= u"lookup a particular case by numeric ID",
        label= "Local ID",
    )
    
    def clean_local_id(self):
        data = self.cleaned_data['local_id']
        try:
            case = Case.objects.get(id=data)
        except Case.DoesNotExist:
            raise forms.ValidationError("no case with that ID")
        return case

class CaseNMFSIDLookupForm(SubmitDetectingForm):
    nmfs_id = forms.CharField(
        #help_text= u"lookup a particular case by numeric ID",
        label= "NMFS case ID",
    )
    
    def clean_nmfs_id(self):
        data = self.cleaned_data['nmfs_id']
        cases = Case.objects.filter(nmfs_id__iexact=data)
        # nmfs_id isn't garanteed to be unique
        if cases.count() < 1:
            raise forms.ValidationError("no case has been marked as corresponding to that NMFS case")
        elif cases.count() > 1:
            case_ids = cases.values_list('id', flat=True).order_by('id')
            raise forms.ValidationError("Multiple cases correspond to that NMFS case. Their local-IDs are: %s" % ', '.join(map(unicode, case_ids)))
        return cases[0]

class CaseYearlyNumberLookupForm(SubmitDetectingForm):
    year = forms.IntegerField(required=True)
    number = forms.IntegerField(
        required= True,
        label= "Number within year",
    )
    
    def clean(self):
        d = self.cleaned_data
        if 'year' in d and 'number' in d:
            try:
                YearCaseNumber.objects.get(year=d['year'], number=d['number'])
            except YearCaseNumber.DoesNotExist:
                raise forms.ValidationError("no case has been assigned that number for that year yet")
        return d

class AnimalSearchForm(forms.Form):

    taxon = TaxonField(
        required= False,
    )

    name = forms.CharField(
        required= False,
        help_text= "search for Animals whose name contains this",
    )

class CaseSearchForm(forms.Form):
    
    after_date = forms.DateTimeField(
        required= False,
        help_text= "enter year-month-day",
        widget= Datepicker,
    )
    before_date = forms.DateTimeField(
        required= False,
        help_text= "enter year-month-day",
        widget= Datepicker,
    )

    # TODO check that after date is before before_date
    
    # TODO get the choices dynamically
    case_type = forms.ChoiceField(
        choices= (
            ('', '<any>'),
            ('e', 'Entanglement'),
            ('s', 'Shipstrike'),
        ),
        required= False,
    )
    
    taxon = TaxonField(
        required= False,
    )
    
    case_name = forms.CharField(
        required= False,
        help_text= "search for Cases whose current or past names contain this"
    )
    
    observation_narrative = forms.CharField(
        required= False,
        help_text= "search for Cases with an observation whose narrative contains this phrase",
    )

    def clean(self):
        earlier = self.cleaned_data.get('after_date')
        later = self.cleaned_data.get('before_date')
        if earlier and later and earlier > later:
            raise forms.ValidationError("the 'after date' should equal or precede the 'before date'")
        return super(CaseSearchForm, self).clean()
        
