import operator

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext

from models import Case, Entanglement, Animal, Observation
from forms import CaseForm, EntanglementForm, observation_forms, MergeCaseForm, AnimalForm, CaseTypeForm, AddCaseForm
from apps.locations.forms import LocationForm
from apps.datetime.forms import DateTimeForm
from apps.vessels.forms import VesselInfoForm

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
        observation = None # None is the default for ModelForm(instance=)
        case = Case.objects.get(id=case_id).detailed
        location = None
        report_datetime = None
        observation_datetime = None
        observer_vessel = None
        template = 'incidents/add_observation.html'

    FormClass = observation_forms[case.detailed_class_name]
    if request.method == 'POST':
        observation_form = FormClass(request.POST, instance=observation)
        location_form = LocationForm(request.POST, instance=location, prefix='location')
        report_datetime_form = DateTimeForm(request.POST, prefix='report', instance=report_datetime)
        observation_datetime_form = DateTimeForm(request.POST, prefix='observation', instance=observation_datetime)
        observer_vessel_form = VesselInfoForm(request.POST, instance=observer_vessel, prefix='vessel')
        # this bit of functionality just checks if all the forms are valid
        valid = reduce(operator.and_, map(lambda f: f.is_valid(), (
            observation_form,
            location_form,
            report_datetime_form,
            observation_datetime_form,
            observer_vessel_form,
        )))
        if valid:
            observation = observation_form.save(commit=False)
            observation.case = case
            observation.location = location_form.save()
            observation.report_datetime = report_datetime_form.save()
            observation.observer_vessel = observer_vessel_form.save()
            observation.observation_datetime = observation_datetime_form.save()
            observation.save()
            # TODO any m2m fields on observations?
            return redirect(observation)
    else:
        observation_form = FormClass(instance=observation)
        location_form = LocationForm(instance=location, prefix='location')
        report_datetime_form = DateTimeForm(prefix='report', instance=report_datetime)
        observation_datetime_form = DateTimeForm(prefix='observation', instance=observation_datetime)
        observer_vessel_form = VesselInfoForm(prefix='vessel', instance=observer_vessel)

    return render_to_response(
        template,
        {
            'case': case,
            'observation': observation,
            'observation_form': observation_form,
            'location_form': location_form,
            'report_datetime_form': report_datetime_form,
            'observation_datetime_form': observation_datetime_form,
            'observer_vessel_form': observer_vessel_form,
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

