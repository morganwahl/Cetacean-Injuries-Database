import operator

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.forms import Media
from django.db import transaction
from django.db.models import Q

from reversion import revision

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.datetime.forms import NiceDateTimeForm
from cetacean_incidents.apps.vessels.forms import ObserverVesselInfoForm
from cetacean_incidents.apps.contacts.forms import ContactForm

from cetacean_incidents import generic_views


from models import Case, Animal, Observation
from forms import CaseTypeForm, CaseForm, observation_forms, MergeCaseForm, AnimalForm, generate_AddCaseForm, case_form_classes, ObservationForm, CaseSearchForm

from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.shipstrikes.forms import StrikingVesselInfoForm
from cetacean_incidents.apps.shipstrikes.models import Shipstrike

@login_required
def create_animal(request):
    if request.method == 'POST':
        form = AnimalForm(request.POST)
        if form.is_valid():
            new_animal = form.save()
            return redirect(new_animal)
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

# TODO merge create_case and add_case
@login_required
def create_case(request):
    caseform_args = {}
    if request.method == 'POST':
        caseform_args = {'data': request.POST}
    case_forms = {}
    for case_type_name, case_form_class in case_form_classes.items():
        case_forms[case_type_name] = case_form_class(prefix=case_type_name, **caseform_args)

    if request.method == 'POST':
        type_form = CaseTypeForm(request.POST)
        if type_form.is_valid():
            # get the relevant AddCaseForm subclass
            case_form = case_forms[type_form.cleaned_data['case_type']]
            if case_form.is_valid():
                new_case = case_form.save()
                return redirect(new_case)
    else:
        type_form = CaseTypeForm()
        
    template_media = Media(
        js= ('jquery/jquery-1.3.2.min.js',),
    )
    
    return render_to_response(
        'incidents/add_case.html',
        {
            'media': reduce( lambda m, f: m + f.media, [type_form] +  case_forms.values(), template_media),
            'type_form': type_form,
            'case_forms': case_forms,
        },
        context_instance= RequestContext(request),
    )

@login_required
def add_case(request, animal_id):
    animal = Animal.objects.get(id=animal_id)

    addcaseform_args = {}
    if request.method == 'POST':
        addcaseform_args = {'data': request.POST}
    addcase_forms = {}
    for case_type_name, case_form_class in case_form_classes.items():
        addcase_forms[case_type_name] = generate_AddCaseForm(case_form_class)(prefix=case_type_name, **addcaseform_args)

    if request.method == 'POST':
        type_form = CaseTypeForm(request.POST)
        if type_form.is_valid():
            # get the relevant AddCaseForm subclass
            case_form = addcase_forms[type_form.cleaned_data['case_type']]
            if case_form.is_valid():
                new_case = case_form.save(commit=False)
                new_case.animal = animal
                new_case.save()
                case_form.save_m2m()
                return redirect(new_case)
    else:
        type_form = CaseTypeForm()
        
    template_media = Media(
        js= ('jquery/jquery-1.3.2.min.js',),
    )
    
    return render_to_response(
        'incidents/add_case.html',
        {
            'animal': animal,
            'media': reduce( lambda m, f: m + f.media, [type_form] +  addcase_forms.values(), template_media),
            'type_form': type_form,
            'case_forms': addcase_forms,
        },
        context_instance= RequestContext(request),
    )

@login_required
def case_detail(request, case_id, extra_context={}):
    case = Case.objects.get(id=case_id).detailed
    return generic_views.object_detail(
        request,
        object_id= case_id,
        queryset= case.__class__.objects.all(),
        template_object_name= 'case',
        extra_context= extra_context,
    )

@login_required
def observation_detail(request, observation_id):
    observation = Observation.objects.get(id=observation_id).detailed
    if not observation.__class__ is Observation:
        # avoid redirect loops!
        # TODO is this the best way to detect that? what if middleware is 
        # altering the URLs?
        # TODO the best would be a decorator function for views that checks if
        # a view's return value is a redirect that will resolve back to the 
        # same view, with the same args
        if observation.get_absolute_url() != request.path:
            return redirect(observation)
    return generic_views.object_detail(
        request,
        object_id= observation_id,
        queryset= Observation.objects.all(),
        template_object_name= 'observation',
    )

@login_required
def add_observation(
        request,
        case_id,
        template='incidents/add_observation.html',
        observationform_class= ObservationForm,
        additional_form_classes= {},
        additional_form_saving= lambda forms, check, observation: None,
    ):
    '''\
    observationform_class, if given, should be a subclass of ObservationForm.
    '''
    case = Case.objects.get(id=case_id).detailed
    
    form_classes = {
        'observation': observationform_class,
        'report_datetime': NiceDateTimeForm,
        'new_reporter': ContactForm,
        'observation_datetime': NiceDateTimeForm,
        'location': NiceLocationForm,
        'new_observer': ContactForm,
        'observer_vessel': ObserverVesselInfoForm,
        'new_vesselcontact': ContactForm,
    }
    form_classes.update(additional_form_classes)
    
    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = {}
        if request.method == 'POST':
            kwargs['data'] = request.POST
        forms[form_name] = form_class(prefix=form_name, **kwargs)

    if request.method == 'POST':
        class _SomeValidationFailed(Exception):
            pass
        def _check(form_name):
            if not forms[form_name].is_valid():
                raise _SomeValidationFailed(form_name, forms[form_name])

        # Revisions should always correspond to transactions!
        @transaction.commit_on_success
        @revision.create_on_success
        def _try_saving():
            _check('observation')
            observation = forms['observation'].save(commit=False)
            observation.case = case

            _check('report_datetime')
            observation.report_datetime = forms['report_datetime'].save()

            if forms['observation'].cleaned_data['new_reporter'] == 'new':
                _check('new_reporter')
                observation.reporter = forms['new_reporter'].save()
            
            _check('observation_datetime')
            observation.observation_datetime = forms['observation_datetime'].save()
            
            _check('location')
            observation.location = forms['location'].save()
            
            if forms['observation'].cleaned_data['new_observer'] == 'new':
                _check('new_observer')
                observation.observer = forms['new_observer'].save()
            elif forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
            
            if forms['observation'].cleaned_data['observer_on_vessel'] == True:
                _check('observer_vessel')
                observer_vessel = forms['observer_vessel'].save(commit=False)
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'new':
                    _check('new_vesselcontact')
                    observer_vessel.contact = forms['new_vesselcontact'].save()
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
                    observer_vessel.contact = observation.reporter
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'observer':
                    observer_vessel.contact = observation.observer
                observer_vessel.save()
                forms['observer_vessel'].save_m2m()
                observation.observer_vessel = observer_vessel
            
            additional_form_saving(forms, _check, observation)
            
            observation.save()
            forms['observation'].save_m2m()
            return observation

        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            print "error in form %s: %s" % (formname, unicode(form.errors))

    template_media = Media(
        css= {'all': ('jqueryui/overcast/jquery-ui-1.7.2.custom.css',)},
        js= ('jquery/jquery-1.3.2.min.js', 'jqueryui/jquery-ui-1.7.2.custom.min.js', 'radiohider.js'),
    )
    
    return render_to_response(
        template,
        {
            'case': case,
            'forms': forms,
            'all_media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_observation(
        request,
        observation_id,
        template='incidents/add_observation.html',
        observationform_class= ObservationForm,
        additional_form_classes= {},
        additional_model_instances = {},
        additional_form_initials= {},
        additional_form_saving= lambda forms, instances, check, observation: None,
    ):
    '''\
    observationform_class, if given, should be a subclass of ObservationForm.
    additioanl_model_instances should have keys that correspond to the ones in
    additional_form_classes.
    '''
    
    form_classes = {
        'observation': observationform_class,
        'report_datetime': NiceDateTimeForm,
        'new_reporter': ContactForm,
        'observation_datetime': NiceDateTimeForm,
        'location': NiceLocationForm,
        'new_observer': ContactForm,
        'observer_vessel': ObserverVesselInfoForm,
        'new_vesselcontact': ContactForm,
    }
    form_classes.update(additional_form_classes)
    
    observation = Observation.objects.get(id=observation_id).detailed

    model_instances = {
        'observation': observation,
        'report_datetime': observation.report_datetime,
        'observation_datetime': observation.observation_datetime,
        'location': observation.location,
        'observer_vessel': observation.observer_vessel,
    }
    model_instances.update(additional_model_instances)

    form_initials = {
        'observation': {},
        'observer_vessel': {},
    }

    form_initials['observation']['observer_on_vessel'] = model_instances['observation'].observer_vessel
    if model_instances['observation'].reporter:
        form_initials['observation']['new_reporter'] = 'other'
    if model_instances['observation'].observer:
        if model_instances['observation'].observer == model_instances['observation'].reporter:
            form_initials['observation']['new_observer'] = 'reporter'
        else:
            form_initials['observation']['new_observer'] = 'observer'

    if model_instances['observer_vessel'] and model_instances['observer_vessel'].contact:
        if model_instances['observer_vessel'].contact == model_instances['observation'].reporter:
            form_initials['observer_vessel']['contact_choice'] = 'reporter'
        if model_instances['observer_vessel'].contact == model_instances['observation'].observer:
            form_initials['observer_vessel']['contact_choice'] = 'observer'
        else:
            form_initials['observer_vessel']['contact_choice'] = 'other'
            form_initials['observer_vessel']['existing_contact'] = model_instances['observer_vessel'].contact

    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = {}
        if request.method == 'POST':
            kwargs['data'] = request.POST
        if form_name in model_instances:
            kwargs['instance'] = model_instances[form_name]
        if form_name in form_initials:
            kwargs['initial'] = form_initials[form_name]
        forms[form_name] = form_class(prefix=form_name, **kwargs)

    if request.method == 'POST':
        class _SomeValidationFailed(Exception):
            pass
        def _check(form_name):
            if not forms[form_name].is_valid():
                raise _SomeValidationFailed(form_name, forms[form_name])

        # Revisions should always correspond to transactions!
        @transaction.commit_on_success
        @revision.create_on_success
        def _try_saving():
            _check('observation')
            observation = forms['observation'].save(commit=False)

            _check('report_datetime')
            observation.report_datetime = forms['report_datetime'].save()

            if forms['observation'].cleaned_data['new_reporter'] == 'new':
                _check('new_reporter')
                observation.reporter = forms['new_reporter'].save()
            
            _check('observation_datetime')
            observation.observation_datetime = forms['observation_datetime'].save()
            
            _check('location')
            observation.location = forms['location'].save()
            
            if forms['observation'].cleaned_data['new_observer'] == 'new':
                _check('new_observer')
                observation.observer = forms['new_observer'].save()
            elif forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
            
            if forms['observation'].cleaned_data['observer_on_vessel'] == True:
                _check('observer_vessel')
                observer_vessel = forms['observer_vessel'].save(commit=False)
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'new':
                    _check('new_vesselcontact')
                    observer_vessel.contact = forms['new_vesselcontact'].save()
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
                    observer_vessel.contact = observation.reporter
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'observer':
                    observer_vessel.contact = observation.observer
                observer_vessel.save()
                forms['observer_vessel'].save_m2m()
                observation.observer_vessel = observer_vessel
            
            additional_form_saving(forms, model_instances, _check, observation)
            
            observation.save()
            forms['observation'].save_m2m()
            return observation

        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            print "error in form %s: %s" % (formname, unicode(form.errors))

    template_media = Media(
        css= {'all': ('jqueryui/overcast/jquery-ui-1.7.2.custom.css',)},
        js= ('jquery/jquery-1.3.2.min.js', 'jqueryui/jquery-ui-1.7.2.custom.min.js', 'radiohider.js'),
    )
    
    return render_to_response(
        template,
        {
            'case': observation.case.detailed,
            'observation': observation,
            'forms': forms,
            'all_media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_case(request, case_id, template='incidents/edit_case.html', form_class=CaseForm):
    case = Case.objects.get(id=case_id).detailed
    if request.method == 'POST':
        form = form_class(request.POST, instance=case)
        if form.is_valid():
            form.save()
            return redirect(case)
    else:
        form = form_class(instance=case)
    return render_to_response(
        template, {
            'taxon': case.probable_taxon,
            'gender': case.probable_gender,
            'form': form,
            'case': case,
        },
        context_instance= RequestContext(request),
    )

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
        context_instance= RequestContext(request),
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

def case_search(request):
    form = CaseSearchForm(request.GET)
    # TODO we make a useless queryset since the template expects a queryset
    cases = Case.objects.filter(id=None)

    if form.is_valid():
        case_order_args = ('-current_yearnumber__year', '-current_yearnumber__number', 'id')
        #cases = Case.objects.all().distinct().order_by(*case_order_args)
        # TODO Oracle doesn't support distinct() on models with TextFields
        cases = Case.objects.all().order_by(*case_order_args)
        # TODO shoulde be ordering such that cases with no date come first
    
        if form.cleaned_data['case_type']:
            # TODO go through different case types automatically
            ct = form.cleaned_data['case_type']
            if ct == 'e':
                #cases = Entanglement.objects.all().distinct().order_by(*case_order_args)
                # TODO Oracle doesn't support distinct() on models with TextFields
                cases = Entanglement.objects.all().order_by(*case_order_args)
            if ct == 's':
                #cases = Shipstrike.objects.all().distinct().order_by(*case_order_args)
                # TODO Oracle doesn't support distinct() on models with TextFields
                cases = Shipstrike.objects.all().order_by(*case_order_args)
        
        if form.cleaned_data['after_date']:
            date = form.cleaned_data['after_date']
            o_date = Q(observation__observation_datetime__year__gte=date.year)
            o_date = o_date & (
                Q(observation__observation_datetime__month__isnull=True)
                | Q(observation__observation_datetime__month__gte=date.month)
            )
            o_date = o_date & (
                Q(observation__observation_datetime__day__isnull=True)
                | Q(observation__observation_datetime__day__gte=date.month)
            )
            r_date = Q(observation__report_datetime__year__gte=date.year)
            r_date = r_date & (
                Q(observation__report_datetime__month__isnull=True)
                | Q(observation__report_datetime__month__gte=date.month)
            )
            r_date = r_date & (
                Q(observation__report_datetime__day__isnull=True)
                | Q(observation__report_datetime__day__gte=date.month)
            )
            cases = cases.filter(o_date | r_date)

        if form.cleaned_data['before_date']:
            date = form.cleaned_data['before_date']
            o_date = Q(observation__observation_datetime__year__lte=date.year)
            o_date = o_date & (
                Q(observation__observation_datetime__month__isnull=True)
                | Q(observation__observation_datetime__month__lte=date.month)
            )
            o_date = o_date & (
                Q(observation__observation_datetime__day__isnull=True)
                | Q(observation__observation_datetime__day__lte=date.month)
            )
            r_date = Q(observation__report_datetime__year__lte=date.year)
            r_date = r_date & (
                Q(observation__report_datetime__month__isnull=True)
                | Q(observation__report_datetime__month__lte=date.month)
            )
            r_date = r_date & (
                Q(observation__report_datetime__day__isnull=True)
                | Q(observation__report_datetime__day__lte=date.month)
            )
            cases = cases.filter(o_date | r_date)
        
        if form.cleaned_data['taxon']:
            t = form.cleaned_data['taxon']
            # TODO handle taxon uncertainty!
            cases = cases.filter(observation__taxon=t)

        if form.cleaned_data['observation_narrative']:
            on = form.cleaned_data['observation_narrative']
            cases = cases.filter(observation__narrative__icontains=on)

    return render_to_response(
        "incidents/case_search.html",
        {
            'form': form,
            'case_list': cases,
        },
        context_instance= RequestContext(request),
    )

