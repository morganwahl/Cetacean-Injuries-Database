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

@login_required
def shipstrike_report_form(request):
    '''\
    A single page to quickly create a new Shipstrike for a new Animal and its
    initial Observation.
    '''

    form_kwargs = {}
    if request.method == 'POST':
        form_kwargs['data'] = request.POST.copy()
    this_year = unicode(datetime.today().year)
    forms = {
        'animal': AnimalForm(prefix='animal', **form_kwargs),
        'case': ShipstrikeForm(prefix='case', **form_kwargs),
        'observation': ShipstrikeObservationForm(prefix='observation', **form_kwargs),
        'new_reporter': ContactForm(prefix='new_reporter', **form_kwargs),
        'location': NiceLocationForm(prefix='location', **form_kwargs),
        'report_datetime': NiceDateTimeForm(prefix='report_time', initial={'year': this_year}, **form_kwargs),
        'observation_datetime': NiceDateTimeForm(prefix='observation_time', initial={'year': this_year}, **form_kwargs),
        'striking_vessel': StrikingVesselInfoForm(prefix='striking_vessel', **form_kwargs),
        'new_striking_vessel_contact': ContactForm(prefix='new_striking_vessel_contact', **form_kwargs),
    }
    
    if request.method == 'POST':
        class _SomeValidationFailed(Exception):
            pass

        # hafta use transactions, since the Case won't validate without an
        # Animal, but we can't fill in an Animal until it's saved, but we
        # don't wanna save unless the Observation, etc. are valid. Note that
        # the Transaction middleware doesn't help since the view method doesn't
        # return an exception if one of the forms was invalid.
        # Revisions should always correspond to transactions!
        @transaction.commit_on_success
        @revision.create_on_success
        def _try_saving():
            if not forms['animal'].is_valid():
                raise _SomeValidationFailed('animal', forms['animal'])
            animal = forms['animal'].save()
            data = request.POST.copy()
            data['case-animal'] = animal.id
            # required fields that have defaults
            # TODO get these automatically
            data['case-valid'] = Case._meta.get_field('valid').default
            # TODO don't repeat yourself... get the Form class and prefix from the existing instance of forms['case']
            forms['case'] = ShipstrikeForm(data, prefix='case')
            
            if not forms['case'].is_valid():
                raise _SomeValidationFailed('case', forms['case'])
            case = forms['case'].save()
            
            if not forms['observation'].is_valid():
                raise _SomeValidationFailed('observation', forms['observation'])
            
            # TODO the commit=False save is necessary because ObservationForm
            # doesn't have a Case field
            observation = forms['observation'].save(commit=False)
            observation.case = case

            # check ObservationForm.new_reporter
            if forms['observation'].cleaned_data['new_reporter'] == 'new':
                if not forms['new_reporter'].is_valid():
                    raise _SomeValidationFailed('new_reporter', forms['new_reporter'])
                observation.reporter = forms['new_reporter'].save()
            
            if forms['observation'].cleaned_data['striking_vessel_info']:
                if not forms['striking_vessel'].is_valid():
                    raise _SomeValidationFailed('striking_vessel', forms['striking_vessel'])
                observation.striking_vessel = forms['striking_vessel'].save()
            
            if not forms['location'].is_valid():
                raise _SomeValidationFailed('location', forms['location'])
            observation.location = forms['location'].save()

            if not forms['report_datetime'].is_valid():
                raise _SomeValidationFailed('report_datetime', forms['report_datetime'])
            observation.report_datetime = forms['report_datetime'].save()

            if not forms['observation_datetime'].is_valid():
                raise _SomeValidationFailed('observation_datetime', forms['observation_datetime'])
            observation.observation_datetime = forms['observation_datetime'].save()

            observation.save()
            forms['observation'].save_m2m()

            return case
        
        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            print "error in form %s: %s" % (formname, unicode(form.errors))

    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js'),
    )

    media = reduce(lambda x, y: x + y.media, forms.itervalues(), template_media)
    
    return render_to_response(
        'shipstrikes/shipstrike_report_form.html',
        {
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

