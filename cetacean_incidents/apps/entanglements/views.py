from datetime import datetime
import operator

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import (
    models,
    transaction,
)
from django.forms import Media
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import (
    Context,
    RequestContext,
)
from django.utils.safestring import mark_safe

from reversion import revision

from cetacean_incidents.decorators import permission_required
from cetacean_incidents import generic_views

from cetacean_incidents.apps.contacts.forms import (
    ContactForm,
    OrganizationForm,
)

from cetacean_incidents.apps.incidents.forms import (
    AnimalForm,
    CaseMergeSourceForm,
)
from cetacean_incidents.apps.incidents.models import (
    Animal,
    Case,
)
from cetacean_incidents.apps.incidents.views import (
    _change_case,
    add_observation,
    case_detail,
    edit_observation,
)
from cetacean_incidents.apps.incidents.views.observation import _change_incident
from cetacean_incidents.apps.incidents.views.tabs import CaseTab

from cetacean_incidents.apps.jquery_ui.tabs import Tab

from models import (
    BodyLocation,
    Entanglement,
    EntanglementObservation,
    GearBodyLocation,
    GearType,
)
from forms import (
    AddEntanglementForm,
    EntanglementForm,
    EntanglementMergeForm,
    EntanglementObservationForm,
    GearAnalysisForm,
    GearAnalysisObservationFormset,
    GearOwnerForm,
    LocationGearSetForm,
)

class EntanglementTab(CaseTab):
    
    default_html_id = 'case-entanglement'
    default_html_display = mark_safe(u"<em>Case</em><br>Entanglement")
    default_template = 'entanglements/edit_case_entanglement_tab.html'
    
    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [self.context['case_form'].non_field_errors()] + map(
                    lambda f: self.context['case_form'][f].errors,
                    # TODO duplicates the list of fields in the template
                    (
                        'nmfs_id',
                        'gear_analyzed',
                    ),
                ),
            )
        )
Entanglement.extra_tab_class = EntanglementTab

@login_required
def entanglement_detail(request, case_id, extra_context):
    
    case = Entanglement.objects.get(id=case_id)
    
    # the entanglement_detail.html template needs jQuery
    if not 'media' in extra_context:
        extra_context['media'] = Media()

    if request.user.has_perms(('incidents.change_entanglement', 'incidents.delete_entanglement')):
        merge_form = CaseMergeSourceForm(destination=case)
        extra_context['merge_form'] = merge_form
        extra_context['media'] += merge_form.media
        extra_context['media'] += Media(js=(settings.JQUERY_FILE,))
    
    if request.user.has_perms((
        'entanglements.change_entanglement',
        'entanglements.view_gearowner',
        'entanglements.add_gearowner',
        'entanglements.change_gearowner',
    )):
        extra_context['media'] += Media(
            js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE),
            css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        )
        forms = _instantiate_gear_analysis_forms(request, case)
        form_media = reduce(lambda m, f: m + f.media, forms.values(), Media())
        extra_context['gear_analysis_forms'] = forms
        extra_context['media'] += form_media
    
        if request.method == 'POST':
            result = _process_gear_analysis_forms(extra_context['gear_analysis_forms'])
            if not result is None:
                return redirect(result)
    
    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js', 'checkboxhider.js'),
    )

    extra_context['media'] += template_media

    return generic_views.object_detail(
        request,
        object_id= case_id,
        queryset= Entanglement.objects.select_related().all(),
        template_object_name= 'case',
        extra_context= extra_context,
    )

@login_required
@permission_required('entanglements.change_entanglement')
def edit_entanglement(request, entanglement_id):
    
    entanglement = Entanglement.objects.get(id=entanglement_id)
    if request.method == 'POST':
        form = EntanglementForm(request.POST, prefix='case', instance=entanglement)
    else:
        form = EntanglementForm(prefix='case', instance=entanglement)
    
    # _change_case will set the context
    tab = EntanglementTab(html_id='case-entanglement')
    
    return _change_case(
        request,
        case= entanglement,
        case_form= form,
        template= 'entanglements/edit_entanglement.html', 
        additional_tabs= [tab]
    )
    
@login_required
@permission_required('entanglements.change_entanglement')
@permission_required('entanglements.view_gearowner')
@permission_required('entanglements.change_gearowner')
def edit_gear_owner(request, entanglement_id):
    entanglement = Entanglement.objects.get(id=entanglement_id)
    gear_owner = entanglement.gear_owner_info

    form_classes = {
        'gear_owner': GearOwnerForm,
        'location_set': LocationGearSetForm,
    }
    model_instances = {}
    form_initials = {}

    if not gear_owner is None:
        model_instances['gear_owner'] = gear_owner
        if gear_owner.location_gear_set:
            model_instances['location_set'] = gear_owner.location_gear_set
            if not 'gear_owner' in form_initials.keys():
                form_initials['gear_owner'] = {}
            form_initials['gear_owner']['location_set_known'] = True

    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = {}
        if request.method == 'POST':
            kwargs['data'] = request.POST
        if form_name in model_instances.keys():
            kwargs['instance'] = model_instances[form_name]
        if form_name in form_initials.keys():
            kwargs['initial'] = form_initials[form_name]
        forms[form_name] = form_class(prefix=form_name, **kwargs)
            
    if request.method == 'POST':
        class _SomeValidationFailed(Exception):
            pass
        def _check(form_name):
            if not forms[form_name].is_valid():
                raise _SomeValidationFailed(form_name, forms[form_name])

        # Revisions should always correspond to transactions!
        @transaction.commit_on_success
        @revision.create_on_success
        def _try_saving():
        
            _check('gear_owner')
            gear_owner = forms['gear_owner'].save()
            entanglement.gear_owner_info = gear_owner
            entanglement.save()
            
            if forms['gear_owner'].cleaned_data['location_set_known']:
                _check('location_set')
                gear_owner.location_gear_set = forms['location_set'].save()
            else:
                loc_set = gear_owner.location_gear_set
                if not loc_set is None:
                    gear_owner.location_gear_set = None
                    gear_owner.save()
                    loc_set.delete()

            gear_owner.save()
            
            return entanglement

        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            print "error in form %s: %s" % (formname, unicode(form.errors))

    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js', 'checkboxhider.js'),
    )
    
    return render_to_response(
        'entanglements/edit_gear_owner.html',
        {
            'case': entanglement,
            'forms': forms,
            'media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

def _instantiate_gear_analysis_forms(request, entanglement):
    gear_owner = entanglement.gear_owner_info

    form_classes = {
        'entanglement': GearAnalysisForm,
        'gear_owner': GearOwnerForm,
        'location_set': LocationGearSetForm,
        'entanglement_observations': GearAnalysisObservationFormset,
    }
    form_kwargs = {
        'entanglement_observations': {
            # the EntanglementObservations for observation that are for 
            # 'entanglement'
            'queryset': EntanglementObservation.objects.filter(observation_ptr__cases=entanglement),
        }
    }
    model_instances = {
        'entanglement': entanglement,
    }
    form_initials = {}

    if not gear_owner is None:
        model_instances['gear_owner'] = gear_owner
        if not 'entanglement' in form_initials.keys():
            form_initials['entanglement'] = {}
        form_initials['entanglement']['has_gear_owner_info'] = True
        if not gear_owner.location_gear_set is None:
            model_instances['location_set'] = gear_owner.location_gear_set
            if not 'gear_owner' in form_initials.keys():
                form_initials['gear_owner'] = {}
            form_initials['gear_owner']['location_set_known'] = True

    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = {}
        if form_name in form_kwargs.keys():
            kwargs = form_kwargs[form_name]
        if request.method == 'POST':
            kwargs['data'] = request.POST
        if form_name in model_instances.keys():
            kwargs['instance'] = model_instances[form_name]
        if form_name in form_initials.keys():
            kwargs['initial'] = form_initials[form_name]
        forms[form_name] = form_class(prefix=form_name, **kwargs)

    return forms

def _process_gear_analysis_forms(forms):
    class _SomeValidationFailed(Exception):
        pass
    def _check(form_name):
        if not forms[form_name].is_valid():
            raise _SomeValidationFailed(form_name, forms[form_name])

    # Revisions should always correspond to transactions!
    @transaction.commit_on_success
    @revision.create_on_success
    def _try_saving():
        _check('entanglement')
        entanglement = forms['entanglement'].save(commit=False)
        _check('entanglement_observations')
        forms['entanglement_observations'].save()
        
        if forms['entanglement'].cleaned_data['has_gear_owner_info']:
            _check('gear_owner')
            gear_owner = forms['gear_owner'].save(commit=False)
            
            if forms['gear_owner'].cleaned_data['location_set_known']:
                _check('location_set')
                gear_owner.location_gear_set = forms['location_set'].save()
            else:
                loc_set = gear_owner.location_gear_set
                if not loc_set is None:
                    gear_owner.location_gear_set = None
                    # TODO saved again below
                    gear_owner.save()
                    loc_set.delete()

            gear_owner.save()
            forms['gear_owner'].save_m2m()
            entanglement.gear_owner_info = gear_owner
        else:
            gear_owner = entanglement.gear_owner_info
            if not gear_owner is None:
                entanglement.gear_owner_info = None
                # TODO saved again below
                entanglement.save()
                gear_owner.delete()

        entanglement.save()
        forms['entanglement'].save_m2m()
        
        return entanglement

    try:
        return _try_saving()
    except _SomeValidationFailed as (formname, form):
        print "error in form %s: %s" % (formname, unicode(form.errors))
    
    return None

@login_required
@permission_required('entanglements.view_gearowner')
@permission_required('entanglements.add_gearowner')
@permission_required('entanglements.change_gearowner')
def edit_gear_analysis_popup(request, entanglement_id):
    entanglement = Entanglement.objects.get(id=entanglement_id)
    
    forms = _instantiate_gear_analysis_forms(request, entanglement)
    
    success = False
    if request.method == 'POST':
        result = _process_gear_analysis_forms(forms)
        success = not bool(result is None)

    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js', 'checkboxhider.js'),
    )
    
    return render_to_response(
        'entanglements/edit_gear_analysis_popup.html',
        {
            'case': entanglement,
            'forms': forms,
            'success': success,
            'media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('entanglements.change_entanglement')
@permission_required('entanglements.add_entanglementobservation')
def add_entanglementobservation(request, animal_id=None, entanglement_id=None):
    '''\
    Create a new Observation with a EntanglementObservation extension and attach
    it to an Entanglement, creating the Entanglement if necessary.
    
    If a entanglement_id is given, that Entanglement's animal will be used and
    animal_id will be ignored.
    '''
    
    animal = None
    cases = None
    if not entanglement_id is None:
        cases = [Entanglement.objects.get(id=entanglement_id)]
        animal = cases[0].animal
    elif not animal_id is None:
        animal = Animal.objects.get(id=animal_id)
    
    case_tab = EntanglementTab(html_id='case-entanglement')
    observation_tab = EntanglementObservationTab(html_id='observation-entanglement')
    
    def saving(forms, instances, check, observation):
        check('entanglement_observation')
        # commiting will fail without first setting ent_oe.observation
        ent_oe = forms['entanglement_observation'].save(commit=False)
        ent_oe.observation_ptr = observation
        ent_oe.save()
        forms['entanglement_observation'].save_m2m()
    
    return _change_incident(
        request,
        animal= animal,
        cases= cases,
        new_case_form_class= AddEntanglementForm,
        additional_new_case_tabs= [case_tab],
        additional_form_classes= {
            'entanglement_observation': EntanglementObservationForm,
        },
        additional_form_saving= saving,
        additional_observation_tabs= [observation_tab],
    )

class EntanglementObservationTab(Tab):
    
    default_html_display = mark_safe(u"<em>Observation</em><br>Entanglement")
    default_template = 'entanglements/edit_observation_entanglement_tab.html'
    required_context_keys = ('forms',)

    def li_error(self):
        return bool(self.context['forms']['entanglement_observation'].errors)

def get_entanglementobservation_view_data(ent_oe):
    
    tab = EntanglementObservationTab(html_id='observation-entanglement')
    
    def saving(forms, instances, check, observation):
        check('entanglement_observation')
        ent_oe = forms['entanglement_observation'].save()
        observation.entanglements_entanglementobservation = ent_oe
        observation.save()

    return {
        'form_classes': {
            'entanglement_observation': EntanglementObservationForm,
        },
        'model_instances': {
            'entanglement_observation': ent_oe,
        },
        'form_saving': saving,
        'tabs': [tab],
    }
    
@login_required
@permission_required('incidents.change_entanglement')
@permission_required('incidents.delete_entanglement')
@permission_required('entanglements.view_gearowner')
@permission_required('entanglements.change_gearowner')
@permission_required('entanglements.add_gearowner')
@permission_required('entanglements.delete_gearowner')
def entanglement_merge(request, destination_id, source_id=None):
    # the "source" case will be deleted and references to it will be change to
    # the "destination" case
    
    destination = Entanglement.objects.get(id=destination_id)
    
    if source_id is None:
        merge_form = CaseMergeSourceForm(destination, request.GET)
        if not merge_form.is_valid():
            return redirect('entanglement_detail', destination.id)
        source = merge_form.cleaned_data['source'].specific_instance()
    else:
        source = Case.objects.get(id=source_id).specific_instance()

    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = EntanglementMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            form.delete()
            return redirect('entanglement_detail', destination.id)
    else:
        form = EntanglementMergeForm(**form_kwargs)
    
    return render_to_response(
        'entanglements/entanglement_merge.html',
        {
            'object_name': 'case',
            'object_name_plural': 'cases',
            'destination': destination,
            'source': source,
            'form': form,
            'media': form.media,
        },
        context_instance= RequestContext(request),
    )

