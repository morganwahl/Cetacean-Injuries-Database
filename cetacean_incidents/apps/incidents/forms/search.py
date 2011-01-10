from django import forms

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker
from cetacean_incidents.apps.taxons.forms import TaxonField

from ..models import Animal, Case, YearCaseNumber

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
    
    observed_after_date = forms.DateTimeField(
        required= False,
        widget= Datepicker,
        help_text= "enter year-month-day",
        label= "Observed on or after"
    )
    observed_before_date = forms.DateTimeField(
        required= False,
        widget= Datepicker,
        help_text= "enter year-month-day",
        label= "Observed on or before"
    )

    reported_after_date = forms.DateTimeField(
        required= False,
        widget= Datepicker,
        help_text= "enter year-month-day",
        label= "Reported on or after"
    )
    reported_before_date = forms.DateTimeField(
        required= False,
        widget= Datepicker,
        help_text= "enter year-month-day",
        label= "Reported on or before"
    )

    # TODO check that after date is before before_date
    
    # TODO get the choices dynamically
    case_type = forms.ChoiceField(
        choices= (
            ('', '<any>'),
            ('c', 'Case'),
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

