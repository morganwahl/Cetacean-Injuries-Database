from django import forms

from cetacean_incidents.apps.search_forms.forms import SubmitDetectingForm

from ..models import (
    Animal,
    Case,
    YearCaseNumber,
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

class AnimalFieldNumberLookupForm(SubmitDetectingForm):
    field_number = forms.CharField(
        help_text= u"look up an animal by it's field number",
        label= "field number",
    )
    
    def clean_field_number(self):
        data = self.cleaned_data['field_number']
        animals = Animal.objects.filter(field_number__iexact=data)
        # field_number isn't garanteed to be unique
        if animals.count() < 1:
            raise forms.ValidationError("no animal in the database has that field number")
        elif animals.count() > 1:
            animal_ids = animals.values_list('id', flat=True).order_by('id')
            raise forms.ValidationError("Multiple animals (in the database) have that field number. Their local-IDs are: %s" % ', '.join(map(unicode, animal_ids)))
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

