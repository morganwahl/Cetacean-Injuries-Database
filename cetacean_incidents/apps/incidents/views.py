import operator

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.forms import Media
from django.forms.formsets import formset_factory
from django.db import transaction
from django.db.models import Q
from django.conf import settings

from reversion import revision

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.datetime.forms import NiceDateTimeForm
from cetacean_incidents.apps.vessels.forms import ObserverVesselInfoForm
from cetacean_incidents.apps.contacts.forms import ContactForm, OrganizationForm
from cetacean_incidents.forms import CaseTypeForm, AnimalChoiceForm

from cetacean_incidents import generic_views

from models import Case, Animal, Observation, YearCaseNumber
from forms import AnimalSearchForm, CaseForm, AddCaseForm, MergeCaseForm, AnimalForm, ObservationForm, CaseSearchForm

from cetacean_incidents.apps.contacts.models import Organization
from cetacean_incidents.apps.taxons.models import Taxon
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

    template_media = Media(js=(settings.JQUERY_FILE, 'checkboxhider.js'))

    return render_to_response(
        'incidents/create_animal.html',
        {
            'form': form,
            'all_media': template_media + form.media
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_animal(request, animal_id):
    animal = Animal.objects.get(id=animal_id)
    form_kwargs = {
        'instance': animal,
    }
    if animal.determined_dead_before or animal.necropsy:
        form_kwargs['initial'] = {
            'dead': True,
        }
    
    if request.method == 'POST':
        form = AnimalForm(request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect('animal_detail', animal.id)
    else:
        form = AnimalForm(**form_kwargs)

    template_media = Media(js=(settings.JQUERY_FILE, 'checkboxhider.js'))

    return render_to_response(
        'incidents/edit_animal.html',
        {
            'animal': animal,
            'form': form,
            'all_media': template_media + form.media
        },
        context_instance= RequestContext(request),
    )
@login_required
def animal_search(request):
    # prefix should be the same as the on used on the homepage
    prefix = 'animal_search'
    form_kwargs = {
        'prefix': 'animal_search',
    }
    if request.GET:
        form_kwargs['data'] = request.GET
    form = AnimalSearchForm(**form_kwargs)
    
    animals = None
    
    if form.is_valid():
        animal_order_args = ('id',)
        #animals = Animal.objects.all().distinct().order_by(*animal_order_args)
        # TODO Oracle doesn't support distinct() on models with TextFields
        animals = Animal.objects.all().order_by(*animal_order_args)
        
        if form.cleaned_data['taxon']:
            t = form.cleaned_data['taxon']
            descendants = Taxon.objects.with_descendants(t)
            animals = animals.filter(Q(determined_taxon__in=descendants) | Q(case__observation__taxon__in=descendants))
        
        # empty string for name is same as None
        if form.cleaned_data['name']:
            name = form.cleaned_data['name']
            animals = animals.filter(name__icontains=name)

    return render_to_response(
        "incidents/animal_search.html",
        {
            'form': form,
            'animal_list': animals,
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
    
# TODO merge add_observation and change_observation
# TODO rename, since it also can add animals and cases
@login_required
def add_observation(
        request,
        animal_id=None,
        case_id=None,
        template='incidents/add_observation.html',
        caseform_class=CaseForm,
        addcaseform_class=AddCaseForm,
        observationform_class= ObservationForm,
        additional_form_classes= {},
        additional_form_saving= lambda forms, check, observation: None,
    ):
    '''\
    The doomsday form-view. If case_id is not None, animal_id is ignored (the case's animal is used instead). If case_id is None, a new Case is created for the animal given in animal_id. If animal_id is None, a new Animal is added as well.
    
    observationform_class, if given, should be a subclass of ObservationForm.
    addcaseform_class should be the same as caseform_class, but without an
    animal field.
    '''
    
    case = None
    if not case_id is None:
        case = Case.objects.get(id=case_id).detailed
        animal_id = case.animal.id
    animal = None
    if not animal_id is None:
        animal = Animal.objects.get(id=animal_id)
    
    # if we're adding a new case, there's no point in having an animal field
    # for it. that would also makes the page non-functional if we're adding a new animal.
    if case_id is None:
        caseform_class = addcaseform_class
    
    form_classes = {
        'animal': AnimalForm,
        'case': caseform_class,
        'observation': observationform_class,
        'report_datetime': NiceDateTimeForm,
        'new_reporter': ContactForm,
        'new_reporter_affiliations': formset_factory(OrganizationForm, extra=2),
        'observation_datetime': NiceDateTimeForm,
        'location': NiceLocationForm,
        'new_observer': ContactForm,
        'new_observer_affiliations': formset_factory(OrganizationForm, extra=2),
        'observer_vessel': ObserverVesselInfoForm,
        'new_vesselcontact': ContactForm,
        'new_vesselcontact_affiliations': formset_factory(OrganizationForm, extra=2),
    }
    form_classes.update(additional_form_classes)
    
    form_kwargs = {}

    if not case is None:
        form_kwargs['case'] = {'instance': case}
    if not animal is None:
        form_kwargs['animal'] = {'instance': animal}

    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = form_kwargs.get(form_name, {})
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
            _check('animal')
            animal = forms['animal'].save()
            
            _check('case')
            case = forms['case'].save(commit=False)
            case.animal = animal
            case.save()
            forms['case'].save_m2m()
            
            _check('observation')
            observation = forms['observation'].save(commit=False)
            observation.case = case

            _check('report_datetime')
            observation.report_datetime = forms['report_datetime'].save()

            if forms['observation'].cleaned_data['new_reporter'] == 'new':
                _check('new_reporter')
                _check('new_reporter_affiliations')
                observation.reporter = forms['new_reporter'].save()
                # add the affiliations from the new_affs_formset
                for org_form in forms['new_reporter_affiliations'].forms:
                    # don't save orgs with blank names.
                    if not 'name' in org_form.cleaned_data:
                        continue
                    org = org_form.save()
                    observation.reporter.affiliations.add(org)
            
            _check('observation_datetime')
            observation.observation_datetime = forms['observation_datetime'].save()
            
            _check('location')
            observation.location = forms['location'].save()
            
            if forms['observation'].cleaned_data['new_observer'] == 'new':
                _check('new_observer')
                _check('new_observer_affiliations')
                observation.observer = forms['new_observer'].save()
                # add the affiliations from the new_affs_formset
                for org_form in forms['new_observer_affiliations'].forms:
                    # don't save orgs with blank names.
                    if not 'name' in org_form.cleaned_data:
                        continue
                    # check if maybe the new org was mentioned in a previously
                    # processed new_aff_formset
                    org_query = Organization.objects.filter(name=org_form.cleaned_data['name'])
                    if org_query.count():
                        org = org_query[0] # orgs shouldn't really have 
                                           # identical names anyway, so just use
                                           # the first one.
                    else:
                        org = org_form.save()
                    observation.observer.affiliations.add(org)
            elif forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
            
            if forms['observation'].cleaned_data['observer_on_vessel'] == True:
                _check('observer_vessel')
                observer_vessel = forms['observer_vessel'].save(commit=False)
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'new':
                    _check('new_vesselcontact')
                    _check('new_vesselcontact_affiliations')
                    observer_vessel.contact = forms['new_vesselcontact'].save()
                    # add the affiliations from the new_affs_formset
                    for org_form in forms['new_vesselcontact_affiliations'].forms:
                        # don't save orgs with blank names.
                        if not 'name' in org_form.cleaned_data:
                            continue
                        # check if maybe the new org was mentioned in a 
                        # previously processed new_aff_formset
                        org_query = Organization.objects.filter(name=org_form.cleaned_data['name'])
                        if org_query.count():
                            org = org_query[0] # orgs shouldn't really have 
                                               # identical names anyway, so just 
                                               # use the first one.
                        else:
                            org = org_form.save()
                        observer_vessel.contact.affiliations.add(org)
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
                    observer_vessel.contact = observation.reporter
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'observer':
                    observer_vessel.contact = observation.observer
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'other':
                    observer_vessel.contact = forms['observer_vessel'].cleaned_data['existing_contact']
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
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'radiohider.js', 'checkboxhider.js', 'selecthider.js'),
    )
    
    return render_to_response(
        template,
        {
            'animal': animal,
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
        caseform_class= CaseForm,
        observationform_class= ObservationForm,
        additional_form_classes= {},
        additional_model_instances = {},
        additional_form_initials= {},
        additional_form_saving= lambda forms, instances, check, observation: None,
    ):
    '''\
    observationform_class, if given, should be a subclass of ObservationForm.
    additional_model_instances should have keys that correspond to the ones in
    additional_form_classes.
    '''
    
    form_classes = {
        'animal': AnimalForm,
        'case': caseform_class,
        'observation': observationform_class,
        'report_datetime': NiceDateTimeForm,
        'new_reporter': ContactForm,
        'new_reporter_affiliations': formset_factory(OrganizationForm, extra=2),
        'observation_datetime': NiceDateTimeForm,
        'location': NiceLocationForm,
        'new_observer': ContactForm,
        'new_observer_affiliations': formset_factory(OrganizationForm, extra=2),
        'observer_vessel': ObserverVesselInfoForm,
        'new_vesselcontact': ContactForm,
        'new_vesselcontact_affiliations': formset_factory(OrganizationForm, extra=2),
    }
    form_classes.update(additional_form_classes)
    
    observation = Observation.objects.get(id=observation_id).detailed
    case = observation.case.detailed
    animal = case.animal

    model_instances = {
        'animal': observation.case.animal,
        'case': observation.case,
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
            form_initials['observer_vessel']['existing_contact'] = model_instances['observer_vessel'].contact.id

    for (form_name, initials) in additional_form_initials.items():
        if form_name in form_initials.keys():
            form_initials[form_name].update(initials)
        else:
            form_initials[form_name] = initials

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
            _check('animal')
            forms['animal'].save()
            
            _check('case')
            forms['case'].save()
            
            _check('observation')
            observation = forms['observation'].save(commit=False)

            _check('report_datetime')
            observation.report_datetime = forms['report_datetime'].save()

            if forms['observation'].cleaned_data['new_reporter'] == 'new':
                _check('new_reporter')
                _check('new_reporter_affiliations')
                observation.reporter = forms['new_reporter'].save()
                # add the affiliations from the new_affs_formset
                for org_form in forms['new_reporter_affiliations'].forms:
                    # don't save orgs with blank names.
                    if not 'name' in org_form.cleaned_data:
                        continue
                    org = org_form.save()
                    observation.reporter.affiliations.add(org)
            
            _check('observation_datetime')
            observation.observation_datetime = forms['observation_datetime'].save()
            
            _check('location')
            observation.location = forms['location'].save()
            
            if forms['observation'].cleaned_data['new_observer'] == 'new':
                _check('new_observer')
                _check('new_observer_affiliations')
                observation.observer = forms['new_observer'].save()
                # add the affiliations from the new_affs_formset
                for org_form in forms['new_observer_affiliations'].forms:
                    # don't save orgs with blank names.
                    if not 'name' in org_form.cleaned_data:
                        continue
                    # check if maybe the new org was mentioned in a previously
                    # processed new_aff_formset
                    org_query = Organization.objects.filter(name=org_form.cleaned_data['name'])
                    if org_query.count():
                        org = org_query[0] # orgs shouldn't really have 
                                           # identical names anyway, so just use
                                           # the first one.
                    else:
                        org = org_form.save()
                    observation.observer.affiliations.add(org)
            elif forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
            
            if forms['observation'].cleaned_data['observer_on_vessel'] == True:
                _check('observer_vessel')
                observer_vessel = forms['observer_vessel'].save(commit=False)
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'new':
                    _check('new_vesselcontact')
                    _check('new_vesselcontact_affiliations')
                    observer_vessel.contact = forms['new_vesselcontact'].save()
                    # add the affiliations from the new_affs_formset
                    for org_form in forms['new_vesselcontact_affiliations'].forms:
                        # don't save orgs with blank names.
                        if not 'name' in org_form.cleaned_data:
                            continue
                        # check if maybe the new org was mentioned in a 
                        # previously processed new_aff_formset
                        org_query = Organization.objects.filter(name=org_form.cleaned_data['name'])
                        if org_query.count():
                            org = org_query[0] # orgs shouldn't really have 
                                               # identical names anyway, so just 
                                               # use the first one.
                        else:
                            org = org_form.save()
                        observer_vessel.contact.affiliations.add(org)
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
                    observer_vessel.contact = observation.reporter
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'observer':
                    observer_vessel.contact = observation.observer
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'other':
                    observer_vessel.contact = forms['observer_vessel'].cleaned_data['existing_contact']
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
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'radiohider.js', 'checkboxhider.js', 'selecthider.js'),
    )
    
    return render_to_response(
        template,
        {
            'animal': animal,
            'case': case,
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
        animal_form = AnimalForm(request.POST, prefix='animal', instance=case.animal)
        form = form_class(request.POST, prefix='case', instance=case)
        if animal_form.is_valid() and form.is_valid():
            animal_form.save()
            form.save()
            return redirect(case)
    else:
        animal_form = AnimalForm(prefix='animal', instance=case.animal)
        form = form_class(prefix='case', instance=case)
    
    template_media = Media(
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE),
    )
    
    return render_to_response(
        template, {
            'animal': case.animal,
            'case': case,
            'forms': {
                'animal': animal_form,
                'case': form,
            },
            'media': form.media + animal_form.media + template_media,
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

def animal_search_json(request):
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

def cases_by_year(request, year=None):
    if year is None:
        from datetime import datetime
        year = datetime.now().year
    year = int(year)
    yearcasenumbers = YearCaseNumber.objects.filter(year__exact=year)
    return render_to_response(
        "incidents/cases_by_year.html",
        {
            'year': year,
            'yearcasenumbers': yearcasenumbers,
        },
        context_instance= RequestContext(request),
    )

def case_search(request, after_date=None, before_date=None):
    # prefix should be the same as the homepage
    prefix = 'case_search'
    form_kwargs = {
        'prefix': prefix,
    }
    if request.GET:
        form_kwargs['data'] = request.GET
    else:
        data = {}
        if not after_date is None:
            data[prefix + '-after_date'] = after_date
        if not before_date is None:
            data[prefix + '-before_date'] = before_date
        if data:
            form_kwargs['data'] = data
    form = CaseSearchForm(**form_kwargs)
    
    cases = None

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
            cases = cases.filter(observation__taxon__in=Taxon.objects.with_descendants(t))

        if form.cleaned_data['case_name']:
            name = form.cleaned_data['case_name']
            cases = cases.filter(names__icontains=name)

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

