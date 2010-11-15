from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.db import transaction
from django.conf import settings

from reversion import revision

from cetacean_incidents.apps.incidents.models import Case

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.datetime.forms import NiceDateTimeForm
from cetacean_incidents.apps.contacts.forms import ContactForm
from cetacean_incidents.apps.incidents.forms import AnimalForm

from cetacean_incidents.apps.incidents.views import edit_case, add_observation, edit_observation

from models import Shipstrike, ShipstrikeObservation
from forms import ShipstrikeObservationForm, ShipstrikeForm, AddShipstrikeForm, StrikingVesselInfoForm, NiceStrikingVesselInfoForm

@login_required
def edit_shipstrike(request, case_id):
    return edit_case(request, case_id=case_id, template='shipstrikes/edit_shipstrike.html', form_class=ShipstrikeForm)

def shipstrikeobservation_detail(request, shipstrikeobservation_id):
    shipstrikeobservation = ShipstrikeObservation.objects.get(id=shipstrikeobservation_id)
    return render_to_response(
        'shipstrikes/shipstrike_observation_detail.html',
        {
            'observation': shipstrikeobservation,
            'media': Media(js=(settings.JQUERY_FILE , 'radiohider.js')),
        },
        context_instance= RequestContext(request),
    )

@login_required
def add_shipstrikeobservation(request, animal_id=None, shipstrike_id=None):
    def _try_saving(forms, check, observation):
        if forms['observation'].cleaned_data['striking_vessel_info'] == True:
            check('striking_vessel')
            striking_vessel = forms['striking_vessel'].save(commit=False)

            contact_choice = forms['striking_vessel'].cleaned_data['contact_choice']
            if contact_choice == 'new':
                check('striking_vessel_contact')
                striking_vessel.contact = forms['striking_vessel_contact'].save()
            elif contact_choice == 'reporter':
                striking_vessel.contact = observation.reporter
            elif contact_choice == 'observer':
                striking_vessel.contact = observation.observer
            elif contact_choice == 'other':
                striking_vessel.contact = forms['striking_vessel'].cleaned_data['existing_contact']

            captain_choice = forms['striking_vessel'].cleaned_data['captain_choice']
            if captain_choice == 'new':
                check('striking_vessel_captain')
                striking_vessel.captain = forms['striking_vessel_captain'].save()
            elif captain_choice == 'reporter':
                striking_vessel.captain = observation.reporter
            elif captain_choice == 'observer':
                striking_vessel.captain = observation.observer
            elif captain_choice == 'vessel':
                striking_vessel.captain = striking_vessel.contact
            elif captain_choice == 'other':
                striking_vessel.captain = forms['striking_vessel'].cleaned_data['existing_captain']
            
            striking_vessel.save()
            forms['striking_vessel'].save_m2m()
            observation.striking_vessel = striking_vessel

    return add_observation(
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
def edit_shipstrikeobservation(request, shipstrikeobservation_id):
    observation = ShipstrikeObservation.objects.get(id=shipstrikeobservation_id)
    form_initials = {
        'observation': {
            'striking_vessel_info': not observation.striking_vessel is None,
        }
    }
    if observation.striking_vessel:
        form_initials['striking_vessel'] = {}

        contact = observation.striking_vessel.contact
        if contact is None:
            form_initials['striking_vessel']['contact_choice'] = 'none'
        elif contact == observation.reporter:
            form_initials['striking_vessel']['contact_choice'] = 'reporter'
        elif contact == observation.observer:
            form_initials['striking_vessel']['contact_choice'] = 'observer'
        else:
            form_initials['striking_vessel']['contact_choice'] = 'other'
            form_initials['striking_vessel']['existing_contact'] = contact.id

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
            if contact_choice == 'new':
                check('striking_vessel_contact')
                observation.striking_vessel.contact = forms['striking_vessel_contact'].save()
            elif contact_choice == 'reporter':
                observation.striking_vessel.contact = observation.reporter
            elif contact_choice == 'observer':
                observation.striking_vessel.contact = observation.observer
            elif contact_choice == 'other':
                observation.striking_vessel.contact = forms['striking_vessel'].cleaned_data['existing_contact']
            else: # contact_choice == 'none'
                observation.striking_vessel.contact = None
            
            captain_choice = forms['striking_vessel'].cleaned_data['captain_choice']
            if captain_choice == 'new':
                check(forms['striking_vessel_captain'])
                observation.striking_vessel.captain = forms['striking_vessel_captain'].save()
            elif captain_choice == 'reporter':
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
    
    return edit_observation(
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

