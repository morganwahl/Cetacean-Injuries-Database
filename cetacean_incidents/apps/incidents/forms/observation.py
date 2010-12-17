from django import forms
from django.core.exceptions import ValidationError

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.uncertain_datetimes.forms import UncertainDateTimeField

from ..models import Observation

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

