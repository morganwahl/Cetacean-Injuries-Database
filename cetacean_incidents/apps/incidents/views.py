import operator

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext

from models import Case, Entanglement, Animal, Observation
from forms import CaseForm, EntanglementForm, observation_forms, MergeCaseForm, AnimalForm, CaseTypeForm, AddCaseForm
from cetacean_incidents.apps.locations.forms import LocationForm
from cetacean_incidents.apps.datetime.forms import DateTimeForm
from cetacean_incidents.apps.vessels.forms import ObserverVesselInfoForm
from cetacean_incidents.apps.contacts.forms import ContactForm

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

    elif not case_id is None:
        case = Case.objects.get(id=case_id).detailed
        observation = None # None is the default for ModelForm(instance=)
        location = None
        report_datetime = None
        observation_datetime = None
        observer_vessel = None
        template = 'incidents/add_observation.html'

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
        'location': LocationForm(data, instance=location, prefix='location'),
        'report_datetime': DateTimeForm(data, prefix='report', instance=report_datetime),
        'observation_datetime': DateTimeForm(data, prefix='observation', instance=observation_datetime),
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

    return render_to_response(
        template,
        {
            'case': case,
            'observation': observation,
            'forms': forms,
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_observation(request, observation_id):
    return _add_or_edit_observation(request, observation_id=observation_id)

@login_required
def add_observation(request, case_id):
    return _add_or_edit_observation(request, case_id=case_id)

@login_required
def edit_case(request, case_id):
    case = Case.objects.get(id=case_id)

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

