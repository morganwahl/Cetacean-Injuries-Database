from itertools import chain
from operator import __and__

from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.uncertain_datetimes.forms import UncertainDateTimeField
from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.contacts.models import Contact
from cetacean_incidents.apps.vessels.forms import VesselInfoForm
from cetacean_incidents.apps.incidents.models import Animal, Case, Observation
from cetacean_incidents.apps.incidents.forms import ObservationForm, CaseForm
from cetacean_incidents.apps.jquery_ui.widgets import Datepicker
from cetacean_incidents.apps.dag.forms import DAGField

from models import Entanglement, EntanglementObservation, GearType, GearOwner, BodyLocation, GearBodyLocation

class InlineRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(
            u'<div>\n%s\n</div>' % u'\n'.join(
                [u'<span>%s</span>' % force_unicode(w) for w in self]
            )
        )

class GearBodyLocationForm(forms.ModelForm):
    '''\
    Form to manipulate GearBodyLocation relations. The location
    field is hidden, and its value should be passed to
    __init__ (either in 'intial' or via 'instance').
    '''
    
    def __init__(self, *args, **kwargs):
        super(GearBodyLocationForm, self).__init__(*args, **kwargs)
        
        if not 'location' in self.initial:
            raise KeyError("location wasn't passed to a GearBodyLocationForm")        
        # transmute the one visible field
        f = self.fields['gear_seen']
        loc = BodyLocation.objects.get(pk=self.initial['location'])
        f.label = loc.name
        f.help_text = loc.definition
        
        # if we're editing an exiting relationship
        if not self.instance.pk is None:
            f.initial = {
                True: 'y',
                False: 'n',
            }[self.instance.gear_seen_here]
    
    def save(self, commit=True):
        inst = super(GearBodyLocationForm, self).save(commit=False)

        if self.cleaned_data['gear_seen'] == 'u':
            if commit:
                inst.delete()
                def save_m2m():
                    pass
                self.save_m2m = save_m2m
                return
            else:
                def save_m2m():
                    self.instance.delete()
                self.save_m2m = save_m2m
        else:
            inst.gear_seen_here = {
                'y': True,
                'n': False,
                'u': None,
            }[self.cleaned_data['gear_seen']]
        
        if commit:
            inst.save()
            self.save_m2m()
        
        return inst
    
    gear_seen = forms.ChoiceField(
        choices=(
            ('y', 'yes'),
            ('n', 'no'),
            ('u', 'unknown'),
        ),
        initial= 'u',
        widget= forms.RadioSelect(renderer=InlineRadioFieldRenderer),
    )
    
    class Meta:
        model = GearBodyLocation
        exclude = ('gear_seen_here', 'observation')
        widgets = {
            'location': forms.HiddenInput,
        }

class EntanglementForm(CaseForm):
    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('gear_types')
    gear_types = DAGField(
        queryset= GearType.objects.all(),
        required= _f.blank != True,
        help_text= 'selecting a type implies the ones above it in the hierarchy',
        label= _f.verbose_name.capitalize(),
    )
    
    class Meta(CaseForm.Meta):
        model = Entanglement
        exclude = 'gear_owner_info'
        widgets = CaseForm.Meta.widgets
        widgets.update({
            'analyzed_date': Datepicker,
        })

class AddEntanglementForm(EntanglementForm):
    
    class Meta(EntanglementForm.Meta):
        exclude = ('gear_owner_info', 'animal')

class EntanglementObservationForm(ObservationForm):

    def __init__(self, *args, **kwargs):
        super(EntanglementObservationForm, self).__init__(*args, **kwargs)

        self.gear_body_location_forms = []
        for loc in BodyLocation.objects.all():
            subform_kwargs = {}

            initial_data = {}
            initial_data['location'] = loc.pk
            obs_id = self.initial.get('id', None)
            if not obs_id is None:
                initial_data['observation'] = obs_id
                instance = GearBodyLocation.objects.filter(observation=obs_id, location=loc.pk)
                if instance.exists():
                    instance = instance[0]
                    subform_kwargs['instance'] = instance
            subform_kwargs['initial'] = initial_data

            if self.prefix:
                subform_kwargs['prefix'] = self.prefix + '-' + loc.name
            else:
                subform_kwargs['prefix'] = loc.name

            if self.data:
                subform_kwargs['data'] = self.data

            self.gear_body_location_forms.append(GearBodyLocationForm(**subform_kwargs))

    def is_valid(self):
        return reduce(
            __and__,
            map(
                lambda form: form.is_valid(),
                [super(EntanglementObservationForm, self)] + self.gear_body_location_forms,
            ),
        )

    def save(self, commit=True):
        result = super(EntanglementObservationForm, self).save(commit)
        if commit:
            for gblf in self.gear_body_location_forms:
                gbl = gblf.save(commit=False)
                gbl.observation = result
                gbl.save()
                gblf.save_m2m()

        # save_m2m() is added by save(), and thus isn't simply overrideable
        else:
            old_save_m2m = self.save_m2m
            def new_save_m2m():
                old_save_m2m()
                for gblf in self.gear_body_location_forms:
                    gbl = gblf.save(commit=False)
                    gbl.observation = self.instance
                    gbl.save()
                    gblf.save_m2m()
            self.save_m2m = new_save_m2m
        
        return result
    
    class Meta(ObservationForm.Meta):
        model = EntanglementObservation
        # TODO how to access superclasses attrs here?
        exclude = getattr(ObservationForm.Meta, 'exclude', tuple())
        # form submission fails if we even include this m2m field (since it 
        # uses in intermediary model)
        exclude += ('gear_body_location',)

class GearOwnerDateField(UncertainDateTimeField):
    
    def __init__(self, *args, **kwargs):
        return super(GearOwnerDateField, self).__init__(
            hidden_subfields=('hour', 'minute', 'second', 'microsecond'),
        )
    
class GearOwnerForm(forms.ModelForm):
    
    location_set_known = forms.BooleanField(
        initial= False,
        required= False,
        label= 'location gear was set is known',
        help_text= "check even if just a vague location is known",
    )
    
    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = GearOwner._meta.get_field('datetime_set')
    datetime_set = GearOwnerDateField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    # ModelForm won't fill in all the handy args for us if we specify our own
    # field
    _f = GearOwner._meta.get_field('datetime_missing')
    datetime_missing = GearOwnerDateField(
        required= _f.blank != True,
        help_text= _f.help_text,
        label= _f.verbose_name.capitalize(),
    )

    class Meta:
        model = GearOwner
        exclude = ('case', 'location_gear_set')

