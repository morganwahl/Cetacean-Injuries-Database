from operator import __and__

from django.conf import settings
from django.db.models import Q
from django import forms
from django.forms.models import modelformset_factory
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.dag.forms import DAGField

from cetacean_incidents.apps.incidents.forms import (
    CaseForm,
    CaseMergeForm,
    CaseSearchForm,
)
from cetacean_incidents.apps.incidents.forms.observation import LocationSearchForm
from cetacean_incidents.apps.incidents.models import Animal

from cetacean_incidents.apps.jquery_ui.widgets import Datepicker

from cetacean_incidents.apps.locations.forms import NiceLocationForm

from cetacean_incidents.apps.merge_form.forms import MergeForm

from cetacean_incidents.apps.search_forms.fields import (
    QueryField,
    MatchOptions,
    MatchOption,
)
from cetacean_incidents.apps.search_forms.forms import (
    SubmitDetectingForm,
    SearchForm,
)
from cetacean_incidents.apps.search_forms.related import HideableForeignKeyQuery

from cetacean_incidents.apps.taxons.forms import TaxonMultipleChoiceField
from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes.forms import UncertainDateTimeField

from cetacean_incidents.apps.utils.forms import InlineRadioFieldRenderer

from models import (
    BodyLocation,
    Entanglement,
    EntanglementObservation,
    GearBodyLocation,
    GearOwner,
    GearTarget,
    GearType,
    LocationGearSet,
)

class GearTargetsWidget(forms.CheckboxSelectMultiple):
    
    class Media:
        js = (settings.JQUERY_FILE, 'geartargets.js')

class GearTargetsField(forms.ModelMultipleChoiceField):
    
    widget = GearTargetsWidget
    
    def __init__(self, *args, **kwargs):
        super(GearTargetsField, self).__init__(*args, **kwargs)
    
    def label_from_instance(self, obj):
        label = render_to_string('geartarget_choice.html', {'gt': obj})
        return mark_safe(label)

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

    class Meta(CaseForm.Meta):
        model = Entanglement
        
        exclude = CaseForm.Meta.exclude
        # exclude all the gear_analysis fields except gear_analyzed
        exclude += tuple(set(Entanglement.gear_analysis_fieldnames()) - set(['gear_analyzed']))
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
    _f = Entanglement._meta.get_field('observed_gear_attributes')
    observed_gear_attributes = DAGField(
        queryset= GearType.objects.all(),
        required= _f.blank != True,
        help_text= 'Selecting a type implies the ones above it in the hierarchy.',
        label= _f.verbose_name.capitalize(),
    )

    has_gear_owner_info = forms.BooleanField(
        initial= False,
        required= False,
        label= 'is there any gear owner info?',
    )

    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('targets')
    targets = GearTargetsField(
        queryset= GearTarget.objects.all(),
        required= _f.blank != True,
        label= _f.verbose_name.capitalize(),
        help_text= u'The targets of this gear. You can choose more than one.',
    )

    class Meta(EntanglementForm.Meta):
        exclude = []
        fields = Entanglement.gear_analysis_fieldnames()

# for use in the formset below
class GearAnalysisObservationForm(forms.ModelForm):
    
    class Meta:
        EntanglementObservation
        fields = (
            'gear_retrieved',
            'gear_retriever',
            'gear_given_date',
            'gear_giver',
        )
        # doesn't seem to be working...
        #widgets = {
        #    'gear_given_date': Datepicker,
        #}

GearAnalysisObservationFormset = modelformset_factory(
    EntanglementObservation,
    form= GearAnalysisObservationForm,
    extra= 0,
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
        label= _f.verbose_name.capitalize(),
        help_text= 'selecting a type implies the ones above it in the hierarchy',
    )

    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('observed_gear_attributes')
    observed_gear_attributes = DAGField(
        queryset= GearType.objects.all(),
        required= _f.blank != True,
        label= _f.verbose_name.capitalize(),
        help_text= 'selecting a type implies the ones above it in the hierarchy',
    )
    
    # need to override the help text when using our own widget partly due to
    # Django bug #9321. Ideally the help text would be part of our own Widget,
    # and we could just add gear_types to Meta.widgets.
    _f = Entanglement._meta.get_field('targets')
    targets = GearTargetsField(
        queryset= GearTarget.objects.all(),
        required= _f.blank != True,
        label= _f.verbose_name.capitalize(),
        help_text= u'The targets of this gear. You can choose more than one.',
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
        widgets = {
            'gear_given_date': Datepicker,
        }

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
            GearBodyLocation.objects.create(observation=self.source, location=loc, gear_seen_here=present)
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

class EntanglementNMFSIDLookupForm(SubmitDetectingForm):
    nmfs_id = forms.CharField(
        help_text= u"find entanglement cases whose entanglement NMFS IDs contain this",
        label= "entanglement NMFS ID",
    )
    
    def clean_nmfs_id(self):
        data = self.cleaned_data['nmfs_id']
        cases = Entanglement.objects.filter(nmfs_id__icontains=data)
        # nmfs_id isn't garanteed to be unique
        if cases.count() < 1:
            raise forms.ValidationError("no case has been marked with an NMFS ID like that")
        return cases
    
    def results(self):
        return self.cleaned_data['nmfs_id']

class GearTypeQueryField(QueryField):
    
    default_match_options = MatchOptions([
        MatchOption('and', 'all of',
            DAGField(queryset=GearType.objects.all())
        ),
        MatchOption('or', 'any of',
            DAGField(queryset=GearType.objects.all())
        ),
    ])

    blank_option = True
    
    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.name
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            if lookup_type == 'and':
                # lookup_value is a list of GearTypes
                if len(lookup_value) == 0:
                    return Q()
                
                # no way to return a Q value for entanglements with each of these
                # gear types :-(
                # this is a so-so workaround
                qs = self.model_field.model.objects
                for gt in lookup_value:
                    # match the gear type or any of it's implied types
                    sub_q = Q(**{
                        lookup_fieldname + '__in': gt.get_all_subtypes(),
                    })
                    qs = qs.filter(sub_q)
                ids = qs.values_list('pk', flat=True)
                q = Q(pk__in=ids)

                return q
        
            if lookup_type == 'or':
                # lookup_value is a list of GearTypes
                if len(lookup_value) == 0:
                    return Q()
                
                all_types = set()
                for gt in lookup_value:
                    all_types |= gt.get_all_subtypes()
                
                q = Q(**{lookup_fieldname + '__in': all_types})
                
                return q

        return super(GearTypeQueryField, self).query(value, prefix)

class GearTargetQueryField(QueryField):
    
    default_match_options = MatchOptions([
        MatchOption('and', 'all of',
            GearTargetsField(queryset=GearTarget.objects.all()),
        ),
        MatchOption('or', 'any of',
            GearTargetsField(queryset=GearTarget.objects.all()),
        ),
    ])
    
    blank_option = True
    
    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.name
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            if lookup_type == 'and':
                # lookup_value is a list of GearTargets
                if len(lookup_value) == 0:
                    return Q()
                
                q = Q()
                # no way to return a Q value for entanglements with each of these
                # targets :-(
                # this is a so-so workaround
                qs = self.model_field.model.objects
                for target in lookup_value:
                    qs = qs.filter(**{lookup_fieldname: target})
                ids = qs.values_list('pk', flat=True)
                q = Q(pk__in=ids)
                
                return q
        
            if lookup_type == 'or':
                # lookup_value is a list of GearTargets
                if len(lookup_value) == 0:
                    return Q()
                
                q = Q(**{lookup_fieldname + '__in': lookup_value})
                
                return q

        return super(GearTargetQueryField, self).query(value, prefix)

class EntanglementSearchForm(CaseSearchForm):
    
    _f = Entanglement._meta.get_field('gear_types')
    gear_types = GearTypeQueryField(
        model_field = _f,
        required= False,
        label= _f.verbose_name.capitalize(),
        # we have to set the help_text ourselves since ManyToManyField alters
        # the field's help_text with instructions for a SelectMultiple widget.
        help_text= 'search for entanglement cases whose analyzed gear has these attributes',
    )

    _f = Entanglement._meta.get_field('observed_gear_attributes')
    observed_gear_attributes = GearTypeQueryField(
        model_field = _f,
        required= False,
        label= _f.verbose_name.capitalize(),
        # we have to set the help_text ourselves since ManyToManyField alters
        # the field's help_text with instructions for a SelectMultiple widget.
        help_text= 'search for entanglement cases whose observed gear has these attributes',
    )
    
    _f = Entanglement._meta.get_field('targets')
    targets = GearTargetQueryField(
        model_field = _f,
        required= False,
        label= _f.verbose_name.capitalize(),
        # we have to set the help_text ourselves since ManyToManyField alters
        # the field's help_text with instructions for a SelectMultiple widget.
        help_text= u'search for entanglement cases with these gear targets',
    )
    
    class GearOwnerSearchForm(SearchForm):
        class LocationGearSetSearchForm(LocationSearchForm):
            class Meta:
                model = LocationGearSet
                exclude = LocationSearchForm.Meta.exclude + ('depth_sigdigs',)
        
        _f = GearOwner._meta.get_field('location_gear_set')
        location_gear_set = HideableForeignKeyQuery(
            model_field= _f,
            subform_class= LocationGearSetSearchForm,
        )

        class Meta:
            model = GearOwner
            exclude = ('id',)

    def __init__(self, user=None, *args, **kwargs):
        super(EntanglementSearchForm, self).__init__(*args, **kwargs)
        if not user is None:
            if user.has_perm('entanglements.view_gearowner'):
                _f = Entanglement._meta.get_field('gear_owner_info')
                # the last field is 'sort_by', so insert before that
                self.fields.insert(-1, 'gear_owner_info', HideableForeignKeyQuery(
                    model_field= _f,
                    subform_class= self.GearOwnerSearchForm,
                ))

    class Meta(CaseSearchForm.Meta):
        model = Entanglement

