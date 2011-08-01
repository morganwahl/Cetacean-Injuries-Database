from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.views.decorators.http import condition

from cetacean_incidents.decorators import (
    permission_required,
    global_etag,
)

from cetacean_incidents.apps.incidents.forms import CaseMergeSourceForm
from cetacean_incidents.apps.incidents.models import Animal
from cetacean_incidents.apps.incidents.views import (
    _change_case,
    _change_incident,
    case_search,
)

from cetacean_incidents.apps.jquery_ui.tabs import Tab

from models import Shipstrike
from forms import (
    AddShipstrikeForm,
    ShipstrikeForm,
    ShipstrikeMergeForm,
    ShipstrikeObservationForm,
    ShipstrikeSearchForm,
    StrikingVesselInfoForm,
)

@login_required
@condition(etag_func=global_etag)
def shipstrike_search(request):
    return case_search(
        request,
        searchform_class= ShipstrikeSearchForm,
        template= u'shipstrikes/shipstrike_search.html',
    )

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

class ShipstrikeObservationTab(Tab):
    
    default_html_display = mark_safe(u"<em>Observation</em><br>Shipstrike")
    default_template = 'shipstrikes/edit_observation_shipstrike_tab.html'
    required_context_keys = ('forms',)
    
    def li_error(self):
        return bool(self.context['forms']['shipstrike_observation'].errors)

# TODO make use of get_shipstrikeobservation_view_data
@login_required
@permission_required('shipstrikes.change_shipstrike')
@permission_required('shipstrikes.add_shipstrikeobservation')
def add_shipstrikeobservation(request, animal_id=None, shipstrike_id=None):
    '''\
    Create a new Observation with a ShipstrikeObservation extension and attach
    it to a Shipstrike, creating the Shipstrike if necessary.
    
    If a shipstrike_id is given, that Shipstrikes's animal will be used and
    animal_id will be ignored.
    '''
    
    animal = None
    cases = None
    if not shipstrike_id is None:
        cases = [Shipstrike.objects.get(id=shipstrike_id)]
        animal = cases[0].animal
    elif not animal_id is None:
        animal = Animal.objects.get(id=animal_id)
    
    tab = ShipstrikeObservationTab(html_id='observation-shipstrike')
    
    def _try_saving(forms, instances, check, observation):
        check('shipstrike_observation')
        # committing will fail without first setting ss_oe.observation
        ss_oe = forms['shipstrike_observation'].save(commit=False)
        ss_oe.observation_ptr = observation
        ss_oe.save()
        forms['shipstrike_observation'].save_m2m()
        
        if forms['shipstrike_observation'].cleaned_data['striking_vessel_info'] == False:
            ss_oe.striking_vessel = None
            ss_oe.save()
        else: # there's striking_vessel data
            check('striking_vessel')
            striking_vessel = forms['striking_vessel'].save()
            
            contact_choice = forms['striking_vessel'].cleaned_data['contact_choice']
            if contact_choice == 'reporter':
                observation.striking_vessel.contact = observation.reporter
            elif contact_choice == 'observer':
                observation.striking_vessel.contact = observation.observer
            # 'new', 'other', and 'none' are handled by NiceVesselInfoForm.save
            
            captain_choice = forms['striking_vessel'].cleaned_data['captain_choice']
            if captain_choice == 'reporter':
                observation.striking_vessel.captain = observation.reporter
            elif captain_choice == 'observer':
                observation.striking_vessel.captain = observation.observer
            # 'new', 'vessel', 'other', and 'none' are handled by StrikingVesselInfoForm.save
            
            striking_vessel.save()
            ss_oe.striking_vessel = striking_vessel
            ss_oe.save()

    return _change_incident(
        request,
        animal= animal,
        cases= cases,
        new_case_form_class= AddShipstrikeForm,
        additional_form_classes= {
            'shipstrike_observation': ShipstrikeObservationForm,
            'striking_vessel': StrikingVesselInfoForm,
        },
        additional_form_saving= _try_saving,
        additional_observation_tabs= [tab]
    )

# data to be passed to _change_incident when editing an Observation
def get_shipstrikeobservation_view_data(ss_oe):

    def saving(forms, instances, check, observation):
        check('shipstrike_observation')
        ss_oe = forms['shipstrike_observation'].save()
        observation.shipstrikes_shipstrikeobservation = ss_oe
        observation.save()

        if forms['shipstrike_observation']['striking_vessel_info']:
            check('striking_vessel')
            striking_vessel = forms['striking_vessel'].save()
            
            contact_choice = forms['striking_vessel'].cleaned_data['contact_choice']
            if contact_choice == 'reporter':
                observation.striking_vessel.contact = observation.reporter
            elif contact_choice == 'observer':
                observation.striking_vessel.contact = observation.observer
            # 'new', 'other', and 'none' are handled by NiceVesselInfoForm.save
            
            captain_choice = forms['striking_vessel'].cleaned_data['captain_choice']
            if captain_choice == 'reporter':
                observation.striking_vessel.captain = observation.reporter
            elif captain_choice == 'observer':
                observation.striking_vessel.captain = observation.observer
            # 'new', 'vessel', 'other', and 'none' are handled by StrikingVesselInfoForm.save

            striking_vessel.save()
            ss_oe.striking_vessel = striking_vessel
            ss_oe.save()

    tab = ShipstrikeObservationTab(html_id='observation-shipstrike')

    return {
        'form_classes': {
            'shipstrike_observation': ShipstrikeObservationForm,
            'striking_vessel': StrikingVesselInfoForm,
        },
        'form_initials': {
            'shipstrike_observation': {
                'striking_vessel_info': not ss_oe.striking_vessel is None,
            },
        },
        'model_instances': {
            'shipstrike_observation': ss_oe,
            'striking_vessel': ss_oe.striking_vessel,
        },
        'form_saving': saving,
        'tabs': [tab],
    }

@login_required
@permission_required('incidents.change_shipstrike')
@permission_required('incidents.delete_shipstrike')
def shipstrike_merge(request, destination_id, source_id=None):
    # the "source" case will be deleted and references to it will be change to
    # the "destination" case
    
    destination = Shipstrike.objects.get(id=destination_id)
    
    if source_id is None:
        merge_form = CaseMergeSourceForm(destination, request.GET)
        if not merge_form.is_valid():
            return redirect('shipstrike_detail', destination.id)
        source = merge_form.cleaned_data['source'].specific_instance()
    else:
        source = Case.objects.get(id=source_id).specific_instance()

    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = ShipstrikeMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            form.delete()
            return redirect('shipstrike_detail', destination.id)
    else:
        form = ShipstrikeMergeForm(**form_kwargs)
    
    return render_to_response(
        'incidents/case_merge.html',
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

