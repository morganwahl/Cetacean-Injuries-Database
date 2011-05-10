from django import forms

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker

from cetacean_incidents.apps.taxons.forms import TaxonField

from ..models import (
    Animal,
    Case,
    YearCaseNumber,
)

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

class AnimalSearchForm(forms.Form):

    taxon = TaxonField(
        required= False,
    )

    name = forms.CharField(
        required= False,
        label= "Name or field number",
        help_text= "search for Animals whose name or field number contains this",
    )

class CaseSearchForm(forms.Form):
    # To be subclass for Entanglements, Shipstrikes, etc.

    # TODO get the choices dynamically
    # TODO change to include/exclude Entanglements/Shipstrikes
    case_type = forms.ChoiceField(
        choices= (
            ('', '<any>'),
            ('c', 'not Entanglement or Shipstrike (other stranding)'),
            ('e', 'Entanglement'),
            ('s', 'Shipstrike'),
        ),
        required= False,
    )

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
    
    taxon = TaxonField(
        required= False,
    )
    
    case_name = forms.CharField(
        required= False,
        help_text= "search for cases whose current or past names contain this"
    )
    
    observation_narrative = forms.CharField(
        required= False,
        help_text= "search for cases with an observation whose narrative contains this phrase",
    )
    
    # TODO put this in entanglements app
    from cetacean_incidents.apps.dag.forms import DAGField
    from cetacean_incidents.apps.entanglements.models import Entanglement
    from cetacean_incidents.apps.entanglements.models import GearType
    gear_types = DAGField(
        queryset= GearType.objects.all(),
        required= False,
        label= 'Gear attributes',
        help_text= 'search for entanglements cases whose observed or analyzed gear has these attributes',
    )
    
    # TODO put this in entanglements app
    from cetacean_incidents.apps.entanglements.models import EntanglementObservation
    disentanglement_outcome = forms.MultipleChoiceField(
        # Note that the empty string would be the ideal key for 'unknown', since
        # that's how the value is represented in the database. However, 
        # CheckboxSelectMultiple normalizes empty-string values to u'on'.
        choices= (('unknown','unknown'),) + EntanglementObservation._meta.get_field('disentanglement_outcome').choices,
        initial= [],
        required= False,
        widget= forms.CheckboxSelectMultiple,
        help_text= "search for entanglement cases with an observation whose disentanglement outcome is one of these",
    )
    
    def clean(self):
        earlier = self.cleaned_data.get('after_date')
        later = self.cleaned_data.get('before_date')
        if earlier and later and earlier > later:
            raise forms.ValidationError("the 'after date' should equal or precede the 'before date'")
        return super(CaseSearchForm, self).clean()

class ObservationSearchForm(forms.Form):

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
    
    taxon = TaxonField(
        required= False,
    )
    
    observation_narrative = forms.CharField(
        required= False,
        help_text= "search for an observation whose narrative contains this phrase",
    )
    
    # TODO put this in entanglements app
    from cetacean_incidents.apps.entanglements.models import EntanglementObservation
    disentanglement_outcome = forms.MultipleChoiceField(
        # Note that the empty string would be the ideal key for 'unknown', since
        # that's how the value is represented in the database. However, 
        # CheckboxSelectMultiple normalizes empty-string values to u'on'.
        choices= (('unknown','unknown'),) + EntanglementObservation._meta.get_field('disentanglement_outcome').choices,
        initial= [],
        required= False,
        widget= forms.CheckboxSelectMultiple,
        help_text= "search for observations whose disentanglement outcome is one of these",
    )

    def clean(self):
        earlier = self.cleaned_data.get('after_date')
        later = self.cleaned_data.get('before_date')
        if earlier and later and earlier > later:
            raise forms.ValidationError("the 'after date' should equal or precede the 'before date'")
        return super(ObservationSearchForm, self).clean()

