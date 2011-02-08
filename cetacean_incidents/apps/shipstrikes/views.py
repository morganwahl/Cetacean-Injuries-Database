from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.db import transaction
from django.conf import settings

from reversion import revision

from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.incidents.models import Case

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.contacts.forms import ContactForm
from cetacean_incidents.apps.incidents.forms import AnimalForm

from cetacean_incidents.apps.incidents.views import _change_case, _change_incident

from models import Shipstrike, ShipstrikeObservation
from forms import ShipstrikeObservationForm, ShipstrikeForm, AddShipstrikeForm, StrikingVesselInfoForm, NiceStrikingVesselInfoForm

@login_required
@permission_required('shipstrikes.change_shipstrike')
def edit_shipstrike(request, case_id):
    
    shipstrike = Shipstrike.objects.get(id=case_id)
    if request.method == 'POST':
        form = ShipstrikeForm(request.POST, prefix='case', instance=shipstrike)
    else:
        form = ShipstrikeForm(prefix='case', instance=shipstrike)
        
    return _change_case(
        request,
        case= shipstrike,
        case_form= form,
        template= 'shipstrikes/edit_shipstrike.html'
    )

@login_required
def shipstrikeobservation_detail(request, obs_id):
    obs = ShipstrikeObservation.objects.get(pk=obs_id)
    return redirect(obs.observation_ptr, permanent=True)

# TODO merge with edit_shipstrikeobservation
@login_required
@permission_required('shipstrikes.change_shipstrike')
@permission_required('shipstrikes.add_shipstrikeobservation')
def add_shipstrikeobservation(request, animal_id=None, shipstrike_id=None):
    def _try_saving(forms, instances, check, observation):
        if forms['observation'].cleaned_data['striking_vessel_info'] == False:
            observation.striking_vessel = None
            observation.save()
        else: # there's striking_vessel data
            check('striking_vessel')
            striking_vessel = forms['striking_vessel'].save()
            
            contact_choice = forms['striking_vessel'].cleaned_data['contact_choice']
            if request.user.has_perm('contacts.add_contact'):
                if contact_choice == 'new':
                    check('striking_vessel_contact')
                    striking_vessel.contact = forms['striking_vessel_contact'].save()
            if contact_choice == 'reporter':
                striking_vessel.contact = observation.reporter
            elif contact_choice == 'observer':
                striking_vessel.contact = observation.observer
            # 'other' and 'none' are handled by NiceVesselInfoForm.save

            captain_choice = forms['striking_vessel'].cleaned_data['captain_choice']
            if request.user.has_perm('contacts.add_contact'):
                if captain_choice == 'new':
                    check('striking_vessel_captain')
                    striking_vessel.captain = forms['striking_vessel_captain'].save()
            if captain_choice == 'reporter':
                striking_vessel.captain = observation.reporter
            elif captain_choice == 'observer':
                striking_vessel.captain = observation.observer
            elif captain_choice == 'vessel':
                striking_vessel.captain = striking_vessel.contact
            elif captain_choice == 'other':
                striking_vessel.captain = forms['striking_vessel'].cleaned_data['existing_captain']
            
            striking_vessel.save()
            observation.striking_vessel = striking_vessel

    return _change_incident(
        request,
        animal_id= animal_id,
        case_id= shipstrike_id,
        template= 'shipstrikes/add_shipstrike_observation.html',
        caseform_class= ShipstrikeForm,
        addcaseform_class= AddShipstrikeForm,
        observationform_class= ShipstrikeObservationForm,
        additional_form_classes= {
            'striking_vessel': NiceStrikingVesselInfoForm,
            'striking_vessel_contact': ContactForm,
            'striking_vessel_captain': ContactForm,
        },
        additional_form_saving= _try_saving,
    )

@login_required
@permission_required('change_shipstrike')
@permission_required('change_shipstrikeobservation')
def edit_shipstrikeobservation(request, shipstrikeobservation_id):
    observation = ShipstrikeObservation.objects.get(id=shipstrikeobservation_id)
    form_initials = {
        'observation': {
            'striking_vessel_info': not observation.striking_vessel is None,
        }
    }
    if observation.striking_vessel:
        form_initials['striking_vessel'] = {}

        captain = observation.striking_vessel.captain
        if captain is None:
            form_initials['striking_vessel']['captain_choice'] = 'none'
        elif captain == observation.reporter:
            form_initials['striking_vessel']['captain_choice'] = 'reporter'
        elif captain == observation.observer:
            form_initials['striking_vessel']['captain_choice'] = 'observer'
        elif captain == contact:
            form_initials['striking_vessel']['captain_choice'] = 'vessel'
        else:
            form_initials['striking_vessel']['captain_choice'] = 'other'
            form_initials['striking_vessel']['existing_captain'] = captain.id
    
    def saving(forms, instances, check, observation):
        if forms['observation']['striking_vessel_info']:
            check('striking_vessel')
            observation.striking_vessel = forms['striking_vessel'].save()
            
            contact_choice = forms['striking_vessel'].cleaned_data['contact_choice']
            if request.user.has_perm('contacts.add_contact'):
                if contact_choice == 'new':
                    check('striking_vessel_contact')
                    observation.striking_vessel.contact = forms['striking_vessel_contact'].save()
            if contact_choice == 'reporter':
                observation.striking_vessel.contact = observation.reporter
            elif contact_choice == 'observer':
                observation.striking_vessel.contact = observation.observer
            # 'other' and 'none' are handled by NiceVesselInfoForm.save
            
            captain_choice = forms['striking_vessel'].cleaned_data['captain_choice']
            if request.user.has_perm('contacts.add_contact'):
                if captain_choice == 'new':
                    check(forms['striking_vessel_captain'])
                    observation.striking_vessel.captain = forms['striking_vessel_captain'].save()
            if captain_choice == 'reporter':
                observation.striking_vessel.captain = observation.reporter
            elif captain_choice == 'observer':
                observation.striking_vessel.captain = observation.observer
            elif captain_choice == 'vessel':
                observation.striking_vessel.captain = observation.striking_vessel.contact
            elif captain_choice == 'other':
                observation.striking_vessel.captain = forms['striking_vessel'].cleaned_data['existing_captain']
            else: # captain_choice == 'none'
                observation.striking_vessel.captain = None

            observation.striking_vessel.save()
    
    return _change_incident(
        request,
        observation_id= shipstrikeobservation_id,
        template= 'shipstrikes/edit_shipstrike_observation.html',
        caseform_class= ShipstrikeForm,
        observationform_class= ShipstrikeObservationForm,
        additional_form_classes= {
            'striking_vessel': NiceStrikingVesselInfoForm,
            'striking_vessel_contact': ContactForm,
            'striking_vessel_captain': ContactForm,
        },
        additional_model_instances= {
            'striking_vessel': observation.striking_vessel
        },
        additional_form_initials= form_initials,
        additional_form_saving= saving,
    )

