import operator

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext
from django.forms import Media
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.db import transaction
from django.db import models
from django.conf import settings
from django.utils.safestring import mark_safe

from reversion import revision

from cetacean_incidents import generic_views
from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.incidents.models import Animal, Case

from cetacean_incidents.apps.jquery_ui.tabs import Tab

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.contacts.forms import ContactForm, OrganizationForm
from cetacean_incidents.apps.incidents.forms import AnimalForm

from cetacean_incidents.apps.incidents.views import case_detail, _change_case, add_observation, edit_observation
from cetacean_incidents.apps.incidents.views.observation import _change_incident
from cetacean_incidents.apps.incidents.views.tabs import CaseTab

from models import Entanglement, GearType, EntanglementObservation, BodyLocation, GearBodyLocation
from forms import EntanglementForm, AddEntanglementForm, EntanglementObservationForm, GearOwnerForm

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
                    (
                        'nmfs_id',
                        'gear_fieldnumber',
                        'gear_analyzed',
                        'analyzed_date',
                        'analyzed_by',
                        'gear_types',
                    ),
                ),
            )
        )
Entanglement.extra_tab_class = EntanglementTab

@login_required
def entanglement_detail(request, case_id, extra_context):
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
@permission_required('entanglements.view_gear_owner')
@permission_required('entanglements.add_gear_owner')
def add_gear_owner(request, entanglement_id):
    # TODO merge in with edit_gear_owner
    entanglement = Entanglement.objects.get(id=entanglement_id)

    form_classes = {
        'gear_owner': GearOwnerForm,
        'location_set': NiceLocationForm,
    }
    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = {}
        if request.method == 'POST':
            kwargs['data'] = request.POST
        forms[form_name] = form_class(prefix=form_name, **kwargs)
            
    if request.method == 'POST':
        class _SomeValidationFailed(Exception):
            pass
        class _NothingToSave(Exception):
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
        'entanglements/add_gear_owner.html',
        {
            'case': entanglement,
            'forms': forms,
            'media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('entanglements.change_entanglement')
@permission_required('entanglements.view_gear_owner')
@permission_required('entanglements.change_gear_owner')
def edit_gear_owner(request, entanglement_id):
    entanglement = Entanglement.objects.get(id=entanglement_id)
    gear_owner = entanglement.gear_owner_info

    form_classes = {
        'gear_owner': GearOwnerForm,
        'location_set': NiceLocationForm,
    }

    form_initials = {
        'gear_owner': {
        }
    }

    if gear_owner.location_gear_set:
        form_initials['gear_owner']['location_set_known'] = True

    model_instances = {
        'gear_owner': gear_owner,
        'location_set': gear_owner.location_gear_set,
    }

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
    
