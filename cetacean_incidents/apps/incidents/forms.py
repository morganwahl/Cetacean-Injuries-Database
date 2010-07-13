from itertools import chain
from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from models import Animal, Case, YearCaseNumber, Observation

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact

case_form_classes = {}
addcase_form_classes = {}
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

class CaseTypeFormMeta(forms.Form.__metaclass__):
    
    def __new__(self, name, bases, dict):
        type_names = []
        type_models = {}
        for c in Case.detailed_classes:
            type_names.append( (c.__name__, c._meta.verbose_name) )
            # type_models's keys should be values of the case_type field
            type_models[c.__name__] = c
        type_names = tuple(type_names)
        
        dict['type_names'] = type_names
        dict['case_type'] = forms.ChoiceField(choices=(('','<select a case type>'),) + type_names)
        dict['type_models'] = type_models
        return super(CaseTypeFormMeta, self).__new__(self, name, bases, dict)

class CaseTypeForm(forms.Form):
    '''\
    A form with the case-type field needed when creating new cases.
    '''
    
    # this form is almost entirely dynamically created
    __metaclass__ = CaseTypeFormMeta

class CaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

    

class MergeCaseForm(forms.ModelForm):
    
    class Meta:
        model = Case

class ObservationForm(forms.ModelForm):
    '''\
    This class merely handles commonalities between the different observation
    types. Should be accopanied by forms for Location, two Datetimes, a 
    VesselInfo, and two Contacts.
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

class SubmitDetectingForm(forms.Form):
    '''\
    A form with a hidden 'submitted' field with value 'yes' if the form was
    submitted. Handy for detecting submission via GET method.
    '''
    
    submitted = forms.CharField(
        widget= forms.HiddenInput,
        initial= 'yes',
    )

class CaseIDLookupForm(SubmitDetectingForm):
    local_id = forms.IntegerField(
        #help_text= u"lookup a particular case by numeric ID",
        label= "Local ID",
    )
    
    def clean_local_id(self):
        data = self.cleaned_data['local_id']
        try:
            Case.objects.get(id=data)
        except Case.DoesNotExist:
            raise forms.ValidationError("no case with that ID")
        return data
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

class CaseSearchForm(forms.Form):
    
    after_date = forms.DateTimeField(
        required= False,
        help_text= "enter year-month-day"
    )
    before_date = forms.DateTimeField(
        required= False,
        help_text= "enter year-month-day"
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
        
