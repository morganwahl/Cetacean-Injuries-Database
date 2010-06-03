import operator
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.forms import Media
from django.forms.models import modelformset_factory
from django.db import transaction

from models import Case, Entanglement, Animal, Observation, GearType, EntanglementObservation, ShipstrikeObservation
from forms import CaseForm, EntanglementForm, observation_forms, MergeCaseForm, AnimalForm, CaseTypeForm, AddCaseForm, EntanglementObservationForm, ShipstrikeObservationForm, ShipstrikeForm, StrikingVesselInfoForm
from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.datetime.forms import DateTimeForm, NiceDateTimeForm
from cetacean_incidents.apps.vessels.forms import ObserverVesselInfoForm
from cetacean_incidents.apps.contacts.forms import ContactForm
import cetacean_incidents

from reversion import revision

@login_required
def create_animal(request):
    if request.method == 'POST':
        form = AnimalForm(request.POST)
        if form.is_valid():
            new_animal = form.save()
            return redirect('add_case', new_animal.id)
    else:
        form = AnimalForm()
    return render_to_response(
        'incidents/create_animal.html',
        {
            'form': form,
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_animal(request, animal_id):
    animal = Animal.objects.get(id=animal_id)
    if request.method == 'POST':
        form = AnimalForm(request.POST, instance=animal)
        if form.is_valid():
            form.save()
            return redirect('animal_detail', animal.id)
    else:
        form = AnimalForm(instance=animal)
    return render_to_response(
        'incidents/edit_animal.html',
        {
            'animal': animal,
            'form': form,
        },
        context_instance= RequestContext(request),
    )

@login_required
def add_case(request, animal_id):
    if request.method == 'POST':
        type_form = CaseTypeForm(request.POST)
        # this instance of CaseForm is just to retrieve the fields from the POST,
        # incase type_form isn't valid
        case_form = AddCaseForm(request.POST)
        if type_form.is_valid():
            # transmogrify the generic Case into a Entanglement, Shipstrike, etc. note that this assumes those more specific cases don't have any required fields.
            CaseModel = CaseTypeForm.type_models[type_form.cleaned_data['case_type']]
            if case_form.is_valid():
                data = request.POST.copy()
                data.update({'animal': animal_id})
                # re-create the case_form with an instance of subclass of Case
                case_form = CaseForm(data, instance=CaseModel())
                new_case = case_form.save()
                return redirect('add_observation', new_case.id)
    else:
        case_form = AddCaseForm()
        type_form = CaseTypeForm()
    return render_to_response(
        'incidents/add_case.html',
        {
            'animal': Animal.objects.get(id=animal_id),
            'type_form': type_form,
            'case_form': case_form,
        },
        context_instance= RequestContext(request),
    )

def _entanglement_detail(request, entanglement):
    return render_to_response(
        'incidents/entanglement_detail.html',
        {
            'case': entanglement,
        },
        context_instance= RequestContext(request),
    )

@login_required
def case_detail(request, case_id):
    case = Case.objects.get(id=case_id).detailed
    if isinstance(case, Entanglement):
        return _entanglement_detail(request, entanglement=case)
    else:
        return cetacean_incidents.generic_views.object_detail(
            request,
            object_id= case_id,
            queryset= Case.objects.all(),
            template_object_name= 'case',
        )

def _entanglement_observation_detail(request, entanglementobservation):
    return render_to_response(
        'incidents/entanglement_observation_detail.html',
        {
            'observation': entanglementobservation,
        },
        context_instance= RequestContext(request),
    )

def _shipstrike_observation_detail(request, shipstikeobservation):
    return render_to_response(
        'incidents/shipstrike_observation_detail.html',
        {
            'observation': shipstikeobservation,
        },
        context_instance= RequestContext(request),
    )

@login_required
def observation_detail(request, observation_id):
    observation = Observation.objects.get(id=observation_id)
    try:
        return _entanglement_observation_detail(request, observation.entanglementobservation)
    except EntanglementObservation.DoesNotExist:
        pass
    try:
        return _shipstrike_observation_detail(request, observation.shipstrikeobservation)
    except ShipstrikeObservation.DoesNotExist:
        pass
    
    # fall back on generic templates
    return cetacean_incidents.generic_views.object_detail(
        request,
        observation_id,
        queryset= Observation.objects.all(),
        template_object_name= 'observation',
    )
        
def _add_or_edit_observation(request, case_id=None, observation_id=None):
    if not observation_id is None:
        observation = Observation.objects.get(id=observation_id)
        # transmogrify the observation instance into one specific to the case type
        case = observation.case.detailed
        observation = case.observation_model.objects.get(observation_ptr=observation)
        location = observation.location
        report_datetime = observation.report_datetime
        observation_datetime = observation.observation_datetime
        observer_vessel = observation.observer_vessel
        template = 'incidents/edit_observation.html'
        if isinstance(case, Entanglement):
            template = 'incidents/edit_entanglement_observation.html'

    elif not case_id is None:
        case = Case.objects.get(id=case_id).detailed
        observation = None # None is the default for ModelForm(instance=)
        location = None
        report_datetime = None
        observation_datetime = None
        observer_vessel = None
        template = 'incidents/add_observation.html'
        if isinstance(case, Entanglement):
            template = 'incidents/add_entanglement_observation.html'

    data = None
    if request.method == 'POST':
        data = request.POST
    FormClass = observation_forms[case.detailed_class_name]
    forms = {
        'observation': FormClass(
            data,
            initial= {'observer_on_vessel': observer_vessel is not None},
            instance= observation
        ),
        'new_reporter': ContactForm(data, prefix='new_reporter'),
        'new_observer': ContactForm(data, prefix='new_observer'),
        'location': NiceLocationForm(data, instance=location, prefix='location'),
        'report_datetime': NiceDateTimeForm(data, prefix='report', instance=report_datetime),
        'observation_datetime': NiceDateTimeForm(data, prefix='observation', instance=observation_datetime),
        'observer_vessel': ObserverVesselInfoForm(data, instance=observer_vessel, prefix='vessel'),
        'new_vesselcontact': ContactForm(data, prefix="new_vesselcontact"),
    }
    # _not_ a deep-copy.
    forms_to_check = forms.copy()
    
    if request.method == 'POST':
        # this 'loop' is just so we can break out when an invalid form is found
        for once in (None,):
            if not forms['observation'].is_valid():
                break
            del forms_to_check['observation']
            
            # check ObservationForm.new_reporter
            if forms['observation'].cleaned_data['new_reporter'] == 'new':
                if not forms['new_reporter'].is_valid():
                    break
            # if the contact is new, we just checked the ContactForm's
            # validity; if it's not new, then we shouldn't check it's
            # validity. either way, remove it from the list
            del forms_to_check['new_reporter']

            # check ObservationForm.new_observer
            if forms['observation'].cleaned_data['new_observer'] == 'new':
                if not forms['new_observer'].is_valid():
                    break
            del forms_to_check['new_observer']
            
            # check ObservationForm.observer_on_vessel
            observer_vessel_exists = forms['observation'].cleaned_data['observer_on_vessel']
            if not observer_vessel_exists:
                # observer_vessel
                del forms_to_check['observer_vessel']
                del forms_to_check['new_vesselcontact']
            else:
                if not forms['observer_vessel'].is_valid():
                    break
                del forms_to_check['observer_vessel']
                # check ObserverVesselInfoForm.new_vesselcontact
                if forms['observer_vessel'].cleaned_data['new_vesselcontact'] == 'new':
                    if not forms['new_vesselcontact'].is_valid():
                        break
                del forms_to_check['new_vesselcontact']
            
            # this bit of functionalness just checks if all the remaining forms are valid
            valid = reduce(operator.and_, map(lambda f: f.is_valid(), forms_to_check.itervalues()))
            if not valid:
                break
            
            # at this point all the forms contain valid data, so start storing
            

            observation = forms['observation'].save(commit=False)
            observation.case = case

            observation.report_datetime = forms['report_datetime'].save()

            if forms['observation'].cleaned_data['new_reporter'] == 'new':
                observation.reporter = forms['new_reporter'].save()
            elif forms['observation'].cleaned_data['new_reporter'] == 'none':
                observation.reporter = None
                # TODO deleting contacts?

            observation.location = forms['location'].save()

            observation.observation_datetime = forms['observation_datetime'].save()

            if forms['observation'].cleaned_data['new_observer'] == 'new':
                observation.observer = forms['new_observer'].save()
            elif forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
            elif forms['observation'].cleaned_data['new_observer'] == 'none':
                observation.observer = None

            if observer_vessel_exists:
                vessel_info = forms['observer_vessel'].save(commit=False)
                if forms['observer_vessel'].cleaned_data['new_vesselcontact'] == 'new':
                    vessel_info.contact = forms['new_vesselcontact'].save()
                elif forms['observer_vessel'].cleaned_data['new_vesselcontact'] == 'reporter':
                    vessel_info.contact = observation.reporter
                elif forms['observer_vessel'].cleaned_data['new_vesselcontact'] == 'observer':
                    vessel_info.contact = observation.observer
                elif forms['observer_vessel'].cleaned_data['new_vesselcontact'] == 'none':
                    vessel_info.contact = None
                vessel_info.save()
                # TODO any m2m fields on Vesselinfo?
                observation.observer_vessel = vessel_info
            else:
                if not observation.observer_vessel is None:
                    vessel_info = observation.observer_vessel
                    observation.observer_vessel = None
                    vessel_info.delete()

            observation.save()
            # TODO any m2m fields on observations?

            return redirect(observation)

    template_media = Media(
        css= {'all': ('jqueryui/overcast/jquery-ui-1.7.2.custom.css',)},
        js= ('jquery/jquery-1.3.2.min.js', 'jqueryui/jquery-ui-1.7.2.custom.min.js', 'radiohider.js'),
    )
    
    return render_to_response(
        template,
        {
            'case': case,
            'observation': observation,
            'forms': forms,
            'all_media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_observation(request, observation_id):
    return _add_or_edit_observation(request, observation_id=observation_id)

@login_required
def add_observation(request, case_id):
    return _add_or_edit_observation(request, case_id=case_id)

def _edit_entanglement(request, entanglement):
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
def edit_case(request, case_id):
    case = Case.objects.get(id=case_id).detailed
    if isinstance(case, Entanglement):
        return _edit_entanglement(request, entanglement=case)

    if request.method == 'POST':
        form = CaseForm(request.POST, instance=case)
        if form.is_valid():
            form.save()
            return redirect(case)
    else:
		form = CaseForm(instance=case)
    return render_to_response('incidents/edit_case.html', {
        'taxon': case.probable_taxon,
        'gender': case.probable_gender,
        'form': form,
        'case': case,
    })

@login_required
def merge_case(request, case1_id, case2_id):
    # synthesize the values from the two cases to create the ones for the merged
    # case. we'll actually be modifiying the 'older' of the two, not creating a
    # new one. 'older' means coming earlier when sorting by case.date.year, 
    # case.yearly_number, ascending. if a case has no date (should only occur
    # if it has no observations yet), it's the "newer" one. if neither case has
    # a date, order them by their database IDs.
    
    # TODO check that the cases (and case.observation_models?) are the same type
    case1 = Case.objects.get(id=case1_id)
    case2 = Case.objects.get(id=case2_id)
    
    # we make case1 the older_case by default, so we only need to check for
    # conditions where case2 is older; if any are found, we switch them
    (older_case, newer_case) = (case1, case2)
    switch = False
    
    # check for null dates
    if older_case.date is None:
        if newer_case.date is not None:
            switch = True
        else:
            # sort by IDs
            if newer_case.id < older_case.id:
                switch = True
    elif newer_case.date is not None:
        if newer_case.date.year < older_case.date.year:
            switch = True
        elif newer_case.date.year == older_case.date.year:
            if newer_case.yearly_number < older_case.yearly_number:
                switch = True
            elif newer_case.yearly_number == older_case.yearly_number:
                # TODO should never get here!
                pass
    
    if newer_case.date is not None:
        if older_case.date is None:
            switch = True
        elif newer_case.date.year < older_case.date.year:
            switch = True
        elif newer_case.date.year == older_case.date.year:
            if newer_case.yearly_number < older_case.yearly_number:
                switch = True
    elif older_case.date is None:
        # sort by IDs
        if newer_case.id < older_case.id:
            switch = True
    
    if switch:
        (older_case, newer_case) = (newer_case, older_case)
    
    if request.method == 'POST':
        form = MergeCaseForm(request.POST, older_case)
        if form.is_valid():
            form.save()
            # make sure we get all the past names
            older_case.names_set = older_case.names_set | newer_case.names_set
            # move all the observations. 
            # TODO not sure if save() func gets called when you do QuerySet.update()...
            for o in newer_case.observation_set.all():
                o.case = older_case
                o.save()
            # delete newer_case
            newer_case.delete()
            return redirect('case_detail', older_case.id)
    else:
        # compare the fields in the two cases, one by one
        
        # animal should be the one from the older_case
        animal = older_case.animal.id
        
        # merge the ole_investigation NullableBoolean
        # abbr. for convience.
        ole_investigation = None
        if not older_case.ole_investigation is None:
            # the older case isn't unknown
            if not newer_case.ole_investigation is None:
                # the newer case isn't unknown
                if older_case.ole_investigation == newer_case.ole_investigation:
                    # two cases are the same
                    ole_investigation = older_case.ole_investigation
            else:
                # the newer case is unknown
                ole_investigation = older_case.ole_investigation
        else:
            # the older case is unknown
            if not newer_case.ole_investigation is None:
                # the newer case isn't
                ole_investigation = newer_case.ole_investigation
        
        form = MergeCaseForm(
            data= {
                'animal': animal,
                'ole_investigation': ole_investigation,
            },
            instance= older_case,
        )
            
    return render_to_response(
        'incidents/merge_case.html',
        {
            'form': form,
            'older_case': older_case,
            'newer_case': newer_case,
        },
    )

def animal_search(request):
    '''\
    Given a request with a query in the 'q' key of the GET string, returns a 
    JSON list of Animals.
    '''
    
    query = u''
    if 'q' in request.GET:
        query = request.GET['q']
    
    words = query.split()
    if words:
        firstword = words[0]
        q = Q(name__icontains=firstword)
        try:
            q |= Q(id__exact=int(firstword))
        except ValueError:
            pass
        results = Animal.objects.filter(q).order_by('-id')
    else:
        results = tuple()
    
    # since we wont have access to the handy properties and functions of the
    # Animal objects, we have to call them now and include their output
    # in the JSON
    animals = []
    for result in results:
        animals.append({
            'id': result.id,
            'name': result.name,
            'display_name': unicode(result),
            'determined_taxon': unicode(result.determined_taxon),
        })
    # TODO return 304 when not changed?
    
    return HttpResponse(json.dumps(animals))

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
            pass

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
    
