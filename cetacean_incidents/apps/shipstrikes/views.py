from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.db import transaction

from reversion import revision

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.datetime.forms import NiceDateTimeForm
from cetacean_incidents.apps.contacts.forms import ContactForm
from cetacean_incidents.apps.incidents.models import Case
from cetacean_incidents.apps.incidents.forms import AnimalForm

from models import ShipstrikeObservation
from forms import ShipstrikeObservationForm, ShipstrikeForm, StrikingVesselInfoForm

def shipstrikeobservation_detail(request, shipstrikeobservation_id):
    shipstrikeobservation = ShipstrikeObservation.objects.get(id=shipstrikeobservation_id)
    return render_to_response(
        'incidents/shipstrike_observation_detail.html',
        {
            'observation': shipstrikeobservation,
        },
        context_instance= RequestContext(request),
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
                if not forms['striking_vessel_info'].is_valid():
                    raise _SomeValidationFailed('striking_vessel_info', forms['striking_vessel_info'])
            
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
        js= ('jquery/jquery-1.3.2.min.js', 'radiohider.js'),
    )

    media = reduce(lambda x, y: x + y.media, forms.itervalues(), template_media)
    
    return render_to_response(
        'incidents/shipstrike_report_form.html',
        {
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

