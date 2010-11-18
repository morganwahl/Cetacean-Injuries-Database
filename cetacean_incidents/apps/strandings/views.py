from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.forms import Media
from django.conf import settings

from cetacean_incidents.apps.incidents.models import Case

from cetacean_incidents.apps.incidents.views import case_detail, edit_case, add_observation, edit_observation

from models import Stranding, StrandingObservation
from forms import StrandingForm, AddStrandingForm, StrandingObservationForm

@login_required
def edit_stranding(request, stranding_id):
    return edit_case(
        request,
        case_id= Stranding.objects.get(id=stranding_id).case_ptr.id,
        template= 'strandings/edit_stranding.html', 
        form_class= StrandingForm,
    )

@login_required
def strandingobservation_detail(request, strandingobservation_id):
    strandingobservation = StrandingObservation.objects.get(id=strandingobservation_id)
    return render_to_response(
        'strandings/stranding_observation_detail.html',
        {
            'observation': strandingobservation,
            'media': Media(js=(settings.JQUERY_FILE, 'radiohider.js')),
        },
        context_instance= RequestContext(request),
    )

@login_required
def add_strandingobservation(request, animal_id=None, stranding_id=None):
    return add_observation(
        request,
        animal_id= animal_id,
        case_id= stranding_id,
        template= 'strandings/add_stranding_observation.html',
        observationform_class= StrandingObservationForm,
        caseform_class= StrandingForm,
        addcaseform_class= AddStrandingForm,
    )

@login_required
def edit_strandingobservation(request, strandingobservation_id):
    return edit_observation(
        request,
        observation_id = strandingobservation_id,
        template= 'strandings/edit_stranding_observation.html',
        observationform_class= StrandingObservationForm,
        caseform_class= StrandingForm,
    )

