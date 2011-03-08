from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django import forms
from django.forms.util import ErrorList

from cetacean_incidents.apps.taxons.forms import TaxonField

from cetacean_incidents.apps.uncertain_datetimes.forms import UncertainDateTimeField

from ..models import (
    Case,
    Observation,
)

class LengthWidget(forms.MultiWidget):
    
    def __init__(self, attrs=None):
        ti_attrs = {'size':'10'}
        other_attrs = None
        if not attrs is None:
            ti_attrs.update(attrs)
            other_attrs = attrs
        widgets = (
            forms.TextInput(attrs=ti_attrs),
            forms.Select(attrs=other_attrs,
                choices= (
                    ('cm', u'centimeters'),
                    ('in', u'inches'),
                    ('ft', u'feet'),
                    ('m',  u'meters'),
                ),
            ),
            forms.Select(attrs=other_attrs,
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

    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = Observation._meta.get_field('animal_length')
    animal_length_and_sigdigs = LengthField(
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
        super(ObservationForm, self).__init__(data, files, auto_id, prefix, initial, error_class, label_suffix, empty_permitted, instance)
    
    def save(self, commit=True):
        obs = super(ObservationForm, self).save(commit=False)
        obs.animal_length = self.cleaned_data['animal_length_and_sigdigs'][0]
        obs.animal_length_sigdigs = self.cleaned_data['animal_length_and_sigdigs'][1]
        if commit:
            obs.save()
            self.save_m2m()
        
        return obs
    
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
        
