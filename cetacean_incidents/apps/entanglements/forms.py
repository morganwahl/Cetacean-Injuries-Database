from itertools import chain
from operator import __and__

from django import forms
from django.forms import fields
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.dag.forms import DAGField

from cetacean_incidents.apps.incidents.forms import (
    CaseForm,
    CaseMergeForm,
    SubmitDetectingForm,
)
from cetacean_incidents.apps.incidents.models import (
    Animal,
    Case,
)

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker

from cetacean_incidents.apps.locations.forms import NiceLocationForm

from cetacean_incidents.apps.merge_form.forms import MergeForm

from cetacean_incidents.apps.taxons.forms import TaxonField
from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes.forms import UncertainDateTimeField

from cetacean_incidents.apps.vessels.forms import VesselInfoForm

from models import (
    BodyLocation,
    Entanglement,
    EntanglementObservation,
    GearAttribute,
    GearBodyLocation,
    GearOwner,
    GearType,
    LocationGearSet,
)

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
        help_text= 'Selecting a type implies the ones above it in the hierarchy.',
        label= _f.verbose_name.capitalize(),
    )
    
    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('gear_attributes')
    gear_attributes = forms.ModelMultipleChoiceField(
        queryset= GearAttribute.objects.all(),
        required= _f.blank != True,
        help_text= None,
        label= _f.verbose_name.capitalize(),
        widget= forms.CheckboxSelectMultiple,
    )

    class Meta(CaseForm.Meta):
        model = Entanglement
        
        exclude = CaseForm.Meta.exclude
        exclude += ('gear_owner_info',)
        widgets = CaseForm.Meta.widgets
        widgets.update({
            'analyzed_date': Datepicker,
        })

class LocationGearSetForm(NiceLocationForm):
    
    class Meta(NiceLocationForm.Meta):
        model = LocationGearSet

class LocationGearSetMergeForm(MergeForm):
    
    # TODO same as LocationMergeForm.as_table
    def as_table(self):
        return render_to_string(
            'location_gear_set_merge_form_as_table.html',
            {
                'object_name': LocationGearSet._meta.verbose_name,
                'object_name_plural': LocationGearSet._meta.verbose_name_plural,
                'destination': self.destination,
                'source': self.source,
                'form': self,
            }
        )
    
    class Meta:
        model = LocationGearSet

class GearAnalysisForm(EntanglementForm):
    '''\
    Like EntanglementForm, but only has the fields relevant to gear-analysis.
    '''
    
    has_gear_owner_info = forms.BooleanField(
        initial= False,
        required= False,
        label= 'is there any gear owner info?',
    )

    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('gear_targets')
    gear_targets = forms.ModelMultipleChoiceField(
        queryset= Taxon.objects.filter(rank__lte=0),
        required= _f.blank != True,
        help_text= None,
        label= _f.verbose_name.capitalize(),
        widget= forms.CheckboxSelectMultiple,
    )

    class Meta(EntanglementForm.Meta):
        exclude = []
        fields = (
            'gear_fieldnumber',
            'gear_analyzed',
            'analyzed_date',
            'analyzed_by',
            'num_gear_types',
            'gear_types',
            'gear_targets',
            'gear_attributes',
            'gear_description',
            'gear_compliant',
            'gear_analysis_comments',
            'gear_analysis_conclusions',
            'gear_kept',
            'gear_kept_where',
        )

class EntanglementMergeForm(CaseMergeForm):
    
    def __init__(self, source, destination, data=None, **kwargs):
        # TODO gear owner info!
        if destination.gear_owner_info:
            raise NotImplementedError("can't yet merge entanglement cases with gear-owner info.")
        if isinstance(source, Entanglement):
            if source.gear_owner_info:
                raise NotImplementedError("can't yet merge entanglement cases with gear-owner info.")
        
        super(EntanglementMergeForm, self).__init__(source, destination, data, **kwargs)
    
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

    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('gear_attributes')
    gear_attributes = forms.ModelMultipleChoiceField(
        queryset= GearAttribute.objects.all(),
        required= _f.blank != True,
        help_text= None,
        label= _f.verbose_name.capitalize(),
        widget= forms.CheckboxSelectMultiple,
    )

    def save(self, commit=True):
        # TODO gear owner info!
        
        return super(EntanglementMergeForm, self).save(commit)

    class Meta:
        model = Entanglement
        # don't even include this field so that an EntanglementMergeForm can't 
        # change the animal of the destination case
        exclude = ('animal',)
        widgets = {
            'analyzed_date': Datepicker,
        }

class AddEntanglementForm(EntanglementForm):
    
    class Meta(EntanglementForm.Meta):
        exclude = ('gear_owner_info', 'animal')

Entanglement.form_class = AddEntanglementForm

class EntanglementObservationForm(forms.ModelForm):

    def _init_gear_body_location_forms(self):
        self.gear_body_location_forms = []
        for loc in BodyLocation.objects.all():
            subform_kwargs = {}

            initial_data = {}
            initial_data['location'] = loc.id
            obs_id = self.initial.get('observation_ptr', None)
            if obs_id is None and self.instance:
                obs_id = self.instance.pk
            if not obs_id is None:
                initial_data['observation'] = obs_id
                instance = GearBodyLocation.objects.filter(observation__pk=obs_id, location__id=loc.id)
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

    def __init__(self, *args, **kwargs):
        super(EntanglementObservationForm, self).__init__(*args, **kwargs)
        self._init_gear_body_location_forms()

    def _gear_body_location_forms_are_valid(self):
        return reduce(
            __and__,
            map(
                lambda form: form.is_valid(),
                self.gear_body_location_forms,
            ),
        )
        
    def is_valid(self):
        return super(EntanglementObservationForm, self).is_valid() and self._gear_body_location_forms_are_valid()

    def _save_gear_body_location_forms(self, commit, result):
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

    def save(self, commit=True):
        result = super(EntanglementObservationForm, self).save(commit)
        self._save_gear_body_location_forms(commit, result)
        return result
    
    class Meta:
        model = EntanglementObservation
        # form submission fails if we even include this m2m field (since it 
        # uses an intermediary model)
        exclude = ('gear_body_location',)

class EntanglementObservationMergeForm(MergeForm, EntanglementObservationForm):

    def __init__(self, *args, **kwargs):
        super(EntanglementObservationMergeForm, self).__init__(*args, **kwargs)
        self._init_gear_body_location_forms()

    def is_valid(self):
        return super(EntanglementObservationMergeForm, self).is_valid() and self._gear_body_location_forms_are_valid()

    def as_table(self):
        return render_to_string(
            'entanglementobservation_merge_form_as_table.html',
            {
                'object_name': EntanglementObservation._meta.verbose_name,
                'object_name_plural': EntanglementObservation._meta.verbose_name_plural,
                'destination': self.destination,
                'source': self.source,
                'form': self,
            }
        )

    def save(self, commit=True):
        # HACK temporarily change self.source's GBLs so that MergeForm.save doesn't make them point to self.destination
        source_gbls = self.source.get_gear_body_locations_dict()
        for gbl in self.source.gearbodylocation_set.all():
            gbl.delete()
        result = super(EntanglementObservationMergeForm, self).save(commit)
        # restore self.source's GBLs
        for loc, present in source_gbls.items():
            if present is None:
                continue
            new_gbl = GearBodyLocation.objects.create(observation=self.source, location=loc, gear_seen_here=present)
        self._save_gear_body_location_forms(commit, result)
        return result
    
    class Meta:
        model = EntanglementObservation
        exclude = ('observation_ptr', 'gear_body_location')

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

class GearOwnerMergeForm(MergeForm):
    
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

    def as_table(self):
        return render_to_string(
            'gearowner_merge_form_as_table.html',
            {
                'object_name': GearOwner._meta.verbose_name,
                'object_name_plural': GearOwner._meta.verbose_name_plural,
                'destination': self.destination,
                'source': self.source,
                'form': self,
            }
        )
    
    class Meta:
        model = GearOwner

class AnimalNMFSIDLookupForm(SubmitDetectingForm):
    nmfs_id = forms.CharField(
        help_text= u"look up an animal by the NMFS ID for one of its entanglement cases",
        label= "entanglement NMFS ID",
    )
    
    def clean_nmfs_id(self):
        data = self.cleaned_data['nmfs_id']
        animals = Animal.objects.filter(case__entanglement__nmfs_id__iexact=data)
        # nmfs_id isn't garanteed to be unique
        if animals.count() < 1:
            raise forms.ValidationError("no entanglement case has been marked with that NMFS ID")
        elif animals.count() > 1:
            animal_ids = animals.values_list('id', flat=True).order_by('id')
            raise forms.ValidationError("Multiple animals have entanglement cases with that NMFS ID. The animals' local-IDs are: %s" % ', '.join(map(unicode, animal_ids)))
        return animals[0]

class EntanglementNMFSIDLookupForm(SubmitDetectingForm):
    nmfs_id = forms.CharField(
        help_text= u"lookup a particular entanglement case by NMFS ID",
        label= "entanglement NMFS ID",
    )
    
    def clean_nmfs_id(self):
        data = self.cleaned_data['nmfs_id']
        cases = Entanglement.objects.filter(nmfs_id__iexact=data)
        # nmfs_id isn't garanteed to be unique
        if cases.count() < 1:
            raise forms.ValidationError("no case has been marked with that NMFS ID")
        elif cases.count() > 1:
            case_ids = cases.values_list('id', flat=True).order_by('id')
            raise forms.ValidationError("Multiple cases have that NMFS ID. Their local-IDs are: %s" % ', '.join(map(unicode, case_ids)))
        return cases[0]

