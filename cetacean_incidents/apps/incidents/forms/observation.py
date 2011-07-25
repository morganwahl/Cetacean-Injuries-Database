from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django import forms
from django.forms.util import ErrorList

from cetacean_incidents.apps.contacts.forms import ContactSearchForm

from cetacean_incidents.apps.documents.forms import DocumentableMergeForm

from cetacean_incidents.apps.locations.models import Location

from cetacean_incidents.apps.search_forms.forms import SearchForm
from cetacean_incidents.apps.search_forms.related import (
    ReverseForeignKeyQuery,
    HideableReverseForeignKeyQuery,
    ForeignKeyQuery,
    HideableForeignKeyQuery,
)

from cetacean_incidents.apps.taxons.forms import (
    TaxonField,
    TaxonQueryField,
)

from cetacean_incidents.apps.uncertain_datetimes.forms import UncertainDateTimeField

from ..models import (
    Case,
    Observation,
)

class LengthWidget(forms.MultiWidget):
    
    def __init__(self, attrs=None):
        widgets = (
            forms.TextInput(attrs={'size':'10'}),
            forms.Select(
                choices= (
                    ('cm', u'centimeters'),
                    ('in', u'inches'),
                    ('ft', u'feet'),
                    ('m',  u'meters'),
                    ('ftm', u'fathoms'),
                ),
            ),
            forms.Select(
                choices= (
                    ('0', u'auto'),
                    ('1', u'1'),
                    ('2', u'2'),
                    ('3', u'3'),
                    ('4', u'4'),
                    ('5', u'5'),
                    ('6', u'6'),
                    ('7', u'7'),
                ),
            ),
        )
        super(LengthWidget, self).__init__(widgets, attrs)
    
    def decompress(self, value):
        if value is None:
            return [u'', 'cm', '0']
        if isinstance(value, tuple):
            return list(value)
        
        raise NotImplementedError
    
class LengthField(forms.MultiValueField):
    '''\
    Presents a widget with a number, a unit and an optional sigdigs dialog.
    Normalizes to a Decimal instance of the lenght in meters, and a integer #
    of significant digits in the original.
    '''
    
    widget = LengthWidget
    
    def __init__(self, *args, **kwargs):
        fields = (
            forms.DecimalField(
                label= u"length",
                required= False,
                min_value=D('0'),
            ), 
            forms.ChoiceField( # the unit
                label= u"unit",
                initial= 'cm',
                choices= (
                    ('cm', u'centimeters'),
                    ('in', u'inches'),
                    ('ft', u'feet'),
                    ('m',  u'meters'),
                    ('ftm', u'fathoms'),
                ),
            ),  
            forms.TypedChoiceField(
                label= u"significant digits",
                initial= '0',
                coerce= int,
                choices= (
                    ('0', u'auto'),
                    ('1', u'1'),
                    ('2', u'2'),
                    ('3', u'3'),
                    ('4', u'4'),
                    ('5', u'5'),
                    ('6', u'6'),
                    ('7', u'7'),
                ),
            ),
        )
        
        super(LengthField, self).__init__(fields=fields, *args, **kwargs)
    
    METER = 1
    CENTIMETER = D('.01') * METER
    INCH = D('2.54') * CENTIMETER
    FOOT = D('12') * INCH
    YARD = D('3') * FOOT
    FATHOM = D('2') * YARD
    
    def compress(self, data_list):
        (length, unit, sigdigs) = data_list
        
        if length is None:
            return (None, None)
        
        # fill in the 'auto' value before converting
        if not sigdigs:
            sign, digits, exponent = length.as_tuple()
            sigdigs = len(digits)
        
        # do the unit version
        length *= {
            'm':  LengthField.METER,
            'cm': LengthField.CENTIMETER,
            'in': LengthField.INCH,
            'ft': LengthField.FOOT,
            'ftm': LengthField.FATHOM,
        }[unit]

        return (length, sigdigs)

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

class BaseObservationForm(forms.ModelForm):
    '''\
    Abstract class for common elements between ObservationForm and ObservationMergeForm
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

    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Observation._meta.get_field('animal_length')
    animal_length_and_sigdigs = LengthField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, initial=None, error_class=ErrorList, label_suffix=':', empty_permitted=False, instance=None):

        if instance:
            if not instance.animal_length is None:
                if initial is None:
                    initial = {}
                if 'animal_length' not in initial:
                    initial['animal_length'] = instance.animal_length
            if not instance.animal_length_sigdigs is None:
                if initial is None:
                    initial = {}
                if 'animal_length_sigdigs' not in initial:
                    initial['animal_length_sigdigs'] = instance.animal_length_sigdigs

        if not initial is None and 'animal_length' in initial:
            if 'animal_length_sigdigs' in initial:
                initial['animal_length_and_sigdigs'] = (initial['animal_length'] * 100, 'cm', initial['animal_length_sigdigs'])

        super(BaseObservationForm, self).__init__(data, files, auto_id, prefix, initial, error_class, label_suffix, empty_permitted, instance)
    
    def save(self, commit=True):
        obs = super(BaseObservationForm, self).save(commit=False)
        obs.animal_length = self.cleaned_data['animal_length_and_sigdigs'][0]
        obs.animal_length_sigdigs = self.cleaned_data['animal_length_and_sigdigs'][1]
        if commit:
            obs.save()
            self.save_m2m()
        
        return obs
    
    class Meta:
        model = Observation
        exclude = ('animal_length', 'animal_length_sigdigs') # these are handled by a LengthField

class ObservationForm(BaseObservationForm):
    '''\
    Should be accopanied by forms for Location, a VesselInfo, and two Contacts.
    '''

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
        # the animal and case(s) for a new observation is set by the view. The
        # one-to-one relations shouldn't be shown.
        exclude = ('animal', 'cases', 'location', 'observer_vessel',
            'animal_length', 'animal_length_sigdigs' # these are handled by a LengthField
        )

class ObservationCasesForm(forms.Form):
    '''\
    Given an Observation instance, produces a form with a checkbox for each Case
    for the observation's animal, with the cases the observation is relevant
    to checked. When save() is called, the observation's cases are changed to
    the ones that are checked.
    '''
    
    # Note that all the fields are added dynamically in __init__
    
    def __init__(self, observation, *args, **kwargs):
        super(ObservationCasesForm, self).__init__(*args, **kwargs)
        
        self.fields['cases'] = forms.ModelMultipleChoiceField(
            queryset= Case.objects.filter(animal=observation.animal),
            required= True, # ensures at least one model is selected
            initial= [c.pk for c in observation.cases.all()],
            widget= forms.CheckboxSelectMultiple,
            label= u"Relevant cases",
            help_text= u"Select the cases this observation is relevant to. Only cases concerning the animal this observation is of are shown.",
            error_messages= {
                'required': u"You must select at least one case."
            }
        )

class ObservationMergeSourceForm(forms.Form):
    
    def __init__(self, destination, *args, **kwargs):
        super(ObservationMergeSourceForm, self).__init__(*args, **kwargs)
        
        self.fields['source'] = forms.ModelChoiceField(
            queryset= Observation.objects.exclude(id=destination.id).filter(animal=destination.animal),
            label= 'other %s' % Observation._meta.verbose_name,
            required= True, # ensures an observation is selected
            initial= None,
            help_text= u"""Choose an observation to merge into this one. That observation will be deleted and references to it will refer to this observation instead.""",
            error_messages= {
                'required': u"You must select an observation."
            },
        )

class ObservationMergeForm(DocumentableMergeForm, BaseObservationForm):
    '''\
    Should be accopanied by merge forms for Location and a VesselInfo.
    '''

    def __init__(self, source, destination, data=None, **kwargs):
        # don't merge observations that aren't already for the same animal
        if source.animal != destination.animal:
            raise ValueError("can't merge observations for different animals!")
        
        super(ObservationMergeForm, self).__init__(source, destination, data, **kwargs)
    
        # handle ObservationExtensions as if they were referenced by a field
        # in Observation, not the other way round
        o2o_refs_to_source = self._get_other_model_o2o_refs_to(self.source)
        o2o_refs_to_destination = self._get_other_model_o2o_refs_to(self.destination)

        # TODO don't hard-code all this stranding and entanglement stuff
        from cetacean_incidents.apps.entanglements.models import EntanglementObservation
        from cetacean_incidents.apps.entanglements.forms import EntanglementObservationMergeForm
        from cetacean_incidents.apps.shipstrikes.models import ShipstrikeObservation
        from cetacean_incidents.apps.shipstrikes.forms import ShipstrikeObservationMergeForm
        oe_subform_classes = {
            EntanglementObservation: EntanglementObservationMergeForm,
            ShipstrikeObservation: ShipstrikeObservationMergeForm,
        }
        
        destination_oes = self.destination.get_observation_extensions()
        source_oes = self.source.get_observation_extensions()
        for oe_class in EntanglementObservation, ShipstrikeObservation:

            destination_oe = None
            # check for a matching destination_oe
            for oe in destination_oes:
                if isinstance(oe, oe_class):
                    destination_oe = oe
            source_oe = None
            # check for a matching source_oe
            for oe in source_oes:
                if isinstance(oe, oe_class):
                    source_oe = oe
            
            # the name of the field on Observation that accesses dest_oe
            fieldname = oe_class._meta.get_field('observation_ptr').related.get_accessor_name()
            
            subform_prefix = fieldname
            if self.prefix:
                subform_prefix = self.prefix + '-' + subform_prefix
            
            if destination_oe is None:
                destination_oe = oe_class(observation_ptr=self.destination)
            if source_oe is None:
                source_oe = oe_class(observation_ptr=self.source)
            
            if not oe_class in oe_subform_classes.keys():
                raise NotImplementedError("%s needs a MergeForm subclass" % oe_class)
            
            # TODO this is a recursive call! need some check to avoid infinite
            # recursion
            self.subforms[fieldname] = oe_subform_classes[oe_class](
                destination= destination_oe,
                source= source_oe,
                data= data,
                prefix= subform_prefix,
            )
            
    def save(self, commit=True):
        # append source import_notes to destination import_notes
        self.destination.import_notes += self.source.import_notes
        
        for c in self.source.cases.all():
            self.destination.cases.add(c)

        return super(ObservationMergeForm, self).save(commit)

    class Meta:
        model = Observation
        # don't even include this field so that a CaseMergeForm can't change the
        # animal of the destination case
        exclude = ('animal', 'cases', 
            'animal_length', 'animal_length_sigdigs', # these are handled by a LengthField
        )

from cetacean_incidents.apps.entanglements.models import EntanglementObservation
from cetacean_incidents.apps.shipstrikes.models import ShipstrikeObservation
from cetacean_incidents.apps.shipstrikes.models import StrikingVesselInfo
    
class ObservationSearchForm(SearchForm):
    
    class ObservationContactSearchForm(ContactSearchForm):
        class Meta(ContactSearchForm.Meta):
            sort_field = False
    
    _f = Observation._meta.get_field_by_name('observer')[0]
    observer = HideableForeignKeyQuery(
        model_field= _f,
        subform= ObservationContactSearchForm,
    )
    
    _f = Observation._meta.get_field_by_name('reporter')[0]
    reporter = HideableForeignKeyQuery(
        model_field= _f,
        subform= ObservationContactSearchForm,
    )
    
    class LocationSearchForm(SearchForm):
        class Meta:
            model = Location
            exclude = ('id', 'import_notes', 'roughness', 'coordinates')
    
    _f = Observation._meta.get_field_by_name('location')[0]
    location = HideableForeignKeyQuery(
        model_field= _f,
        subform= LocationSearchForm,
    )

    _f = Observation._meta.get_field_by_name('taxon')[0]
    taxon = TaxonQueryField(model_field= _f, required=False)

    # TODO dynamically get all the ObservationExtensions
    
    class EntanglementObservationSearchForm(SearchForm):
        class Meta:
            model = EntanglementObservation

    _f = EntanglementObservation._meta.get_field_by_name('observation_ptr')[0]
    eos = HideableReverseForeignKeyQuery(
        label= 'entanglement fields',
        model_field= _f,
        subform= EntanglementObservationSearchForm,
        #help_text= "Search entanglement-specific fields."
    )
    
    class ShipstrikeObservationSearchForm(SearchForm):
        
        class ShipstrikeObservationStrikingVesselSearchForm(SearchForm):
            class Meta:
                model = StrikingVesselInfo
                exclude = ('id', 'import_notes')
        
        _f = ShipstrikeObservation._meta.get_field_by_name('striking_vessel')[0]
        striking_vessel = ForeignKeyQuery(
            model_field= _f,
            subform= ShipstrikeObservationStrikingVesselSearchForm,
        )
        
        class Meta:
            model = ShipstrikeObservation

    _f = ShipstrikeObservation._meta.get_field_by_name('observation_ptr')[0]
    ssos = HideableReverseForeignKeyQuery(
        label= 'shipstrike fields',
        model_field= _f,
        subform= ShipstrikeObservationSearchForm,
        #help_text= "Search entanglement-specific fields."
    )

    class Meta:
        model = Observation
        exclude = ('id', 'import_notes', 'exam', 'initial', 'animal_length_sigdigs')
        sort_field = True

