from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.forms.models import modelformset_factory
from django.db import transaction

from reversion import revision

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.datetime.forms import NiceDateTimeForm
from cetacean_incidents.apps.contacts.forms import ContactForm
from cetacean_incidents.apps.incidents.models import Case
from cetacean_incidents.apps.incidents.forms import observation_forms, AnimalForm

from models import Entanglement, GearType
from forms import EntanglementForm, EntanglementObservationForm

@login_required
def entanglement_detail(request, entanglement_id):
    entanglement = Entanglement.objects.get(id=entanglement_id)
    return render_to_response(
        'incidents/entanglement_detail.html',
        {
            'case': entanglement,
        },
        context_instance= RequestContext(request),
    )

@login_required
def entanglementobservation_detail(request, entanglementobservation):
    return render_to_response(
        'incidents/entanglement_observation_detail.html',
        {
            'observation': entanglementobservation,
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_entanglement(request, entanglement_id):
    entanglement = Entanglement.objects.get(id=entanglement_id)
    if request.method == 'POST':
        form = EntanglementForm(request.POST, instance=entanglement)
        if form.is_valid():
            form.save()
            return redirect(entanglement)
    else:
		form = EntanglementForm(instance=entanglement)
    return render_to_response('incidents/edit_entanglement.html', {
        'taxon': entanglement.probable_taxon,
        'gender': entanglement.probable_gender,
        'form': form,
        'case': entanglement,
    })

@login_required
def entanglement_report_form(request):
    '''\
    A single page to quickly create a new Entanglement for a new Animal and its
    initial Observation.
    '''

    # fill in some defaults specific to this view
    data = None
    if request.method == 'POST':
        data = request.POST.copy()
    this_year = unicode(datetime.today().year)
    forms = {
        'animal': AnimalForm(data, prefix='animal'),
        'case': EntanglementForm(data, prefix='case'),
        'observation': EntanglementObservationForm(data, prefix='observation'),
        'new_reporter': ContactForm(data, prefix='new_reporter'),
        'location': NiceLocationForm(data, prefix='location'),
        'report_datetime': NiceDateTimeForm(data, prefix='report_time', initial={'year': this_year}),
        'observation_datetime': NiceDateTimeForm(data, prefix='observation_time', initial={'year': this_year}),
        'geartypes': modelformset_factory(GearType, extra=3)(),
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
            data['case-animal'] = animal.id
            # required fields that have defaults
            # TODO get these automatically
            data['case-valid'] = Case._meta.get_field('valid').default
            # TODO don't repeat yourself... get the Form class and prefix from the existing instance of forms['case']
            forms['case'] = EntanglementForm(data, prefix='case')
            
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
        'incidents/entanglement_report_form.html',
        {
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

