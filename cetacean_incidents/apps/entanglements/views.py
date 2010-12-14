from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.db import transaction
from django.db import models
from django.conf import settings

from reversion import revision

from cetacean_incidents import generic_views
from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.incidents.models import Case

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.contacts.forms import ContactForm, OrganizationForm
from cetacean_incidents.apps.incidents.forms import AnimalForm

from cetacean_incidents.apps.incidents.views import case_detail, edit_case, add_observation, edit_observation

from models import Entanglement, GearType, EntanglementObservation, BodyLocation, GearBodyLocation
from forms import EntanglementForm, AddEntanglementForm, EntanglementObservationForm, GearOwnerForm

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
    return edit_case(
        request,
        case_id= Entanglement.objects.get(id=entanglement_id).case_ptr.id,
        template= 'entanglements/edit_entanglement.html', 
        form_class= EntanglementForm,
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
            'all_media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
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
            'all_media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
def entanglementobservation_detail(request, entanglementobservation_id):
    entanglementobservation = EntanglementObservation.objects.get(id=entanglementobservation_id)
    body_locations = []
    for loc in BodyLocation.objects.all():
        gear_loc = GearBodyLocation.objects.filter(observation=entanglementobservation, location=loc)
        if gear_loc.exists():
            body_locations.append((loc, gear_loc[0]))
        else:
            body_locations.append((loc, None))
    return render_to_response(
        'entanglements/entanglement_observation_detail.html',
        {
            'observation': entanglementobservation,
            'gear_body_locations': body_locations,
            'media': Media(js=(settings.JQUERY_FILE, 'radiohider.js')),
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('entanglements.change_entanglement')
@permission_required('entanglements.add_entanglementobservation')
def add_entanglementobservation(request, animal_id=None, entanglement_id=None):
    return add_observation(
        request,
        animal_id= animal_id,
        case_id= entanglement_id,
        template= 'entanglements/add_entanglement_observation.html',
        observationform_class= EntanglementObservationForm,
        caseform_class= EntanglementForm,
        addcaseform_class= AddEntanglementForm,
    )

@login_required
@permission_required('entanglements.change_entanglement')
@permission_required('entanglements.change_entanglementobservation')
def edit_entanglementobservation(request, entanglementobservation_id):
    return edit_observation(
        request,
        observation_id = entanglementobservation_id,
        template= 'entanglements/edit_entanglement_observation.html',
        observationform_class= EntanglementObservationForm,
        caseform_class= EntanglementForm,
    )

