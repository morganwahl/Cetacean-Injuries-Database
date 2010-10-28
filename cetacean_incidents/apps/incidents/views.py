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
from cetacean_incidents.forms import CaseTypeForm, AnimalChoiceForm, merge_source_form_factory

from cetacean_incidents import generic_views

from models import Case, Animal, Observation, YearCaseNumber
from forms import AnimalSearchForm, AnimalMergeForm, CaseForm, AddCaseForm, MergeCaseForm, AnimalForm, ObservationForm, CaseSearchForm

from cetacean_incidents.apps.contacts.models import Organization
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.shipstrikes.forms import StrikingVesselInfoForm
from cetacean_incidents.apps.shipstrikes.models import Shipstrike

@login_required
def animal_detail(request, animal_id):
    
    animal = Animal.objects.get(id=animal_id)
    
    merge_form = merge_source_form_factory(Animal, animal)()
    template_media = Media(
        js= (settings.JQUERY_FILE,),
    )
    
    return render_to_response(
        'incidents/animal_detail.html',
        {
            'animal': animal,
            'media': template_media + merge_form.media,
            'merge_form': merge_form,
        },
        context_instance= RequestContext(request),
    )

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
def animal_merge(request, destination_id, source_id=None):
    # the "source" animal will be deleted and references to it will be change to
    # the "destination" animal
    
    destination = Animal.objects.get(id=destination_id)
    
    if source_id is None:
        merge_form = merge_source_form_factory(Animal, destination)(request.GET)
        if not merge_form.is_valid():
            return redirect('animal_detail', destination.id)
        source = merge_form.cleaned_data['source']
    else:
        source = Animal.objects.get(id=source_id)

    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = AnimalMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect('animal_detail', destination.id)
    else:
        form = AnimalMergeForm(**form_kwargs)
    
    return render_to_response(
        'incidents/animal_merge.html',
        {
            'destination': destination,
            'source': source,
            'form': form,
            'destination_fk_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.destination_fk_refs
            ),
            'source_fk_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.source_fk_refs
            ),
            'destination_m2m_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.destination_m2m_refs
            ),
            'source_m2m_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.source_m2m_refs
            ),
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
    
    animal_list = tuple()
    
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

        # simulate distinct() for Oracle
        # an OrderedSet in the collections library would be nice...
        # TODO not even a good workaround, since we have to pass in the count
        # seprately
        seen = set()
        animal_list = list()
        for a in animals:
            if not a in seen:
                seen.add(a)
                animal_list.append(a)

    return render_to_response(
        "incidents/animal_search.html",
        {
            'form': form,
            'animal_list': animal_list,
            'animal_count': len(animal_list),
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
        taxon = animal.taxon()
        gender = animal.gender()
        if taxon or gender:
            form_kwargs['observation'] = {'initial': {}}
        if taxon:
            form_kwargs['observation']['initial']['taxon'] = taxon
        if gender:
            form_kwargs['observation']['initial']['gender'] = gender

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
            form_initials['observation']['new_observer'] = 'other'

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
    
    case_list = tuple()

    if form.is_valid():

        manager = Case.objects
        if form.cleaned_data['case_type']:
            # TODO go through different case types automatically
            ct = form.cleaned_data['case_type']
            if ct == 'e':
                manager = Entanglement.objects
            if ct == 's':
                manager = Shipstrike.objects
        
        query = Q()
    
        if form.cleaned_data['after_date']:
            # 'before_date' and 'after_date' really search the
            # observation_datetime and report_datetime of observations
            
            # possible matches are:
            #  <year>-null-null
            #  <year>-<month>-null
            #  <year>-<month>-day
            #
            # in other words, where o is observation_date and q is query_date:
            #  (o.year >= q.year & o.month is null)
            #  | (o.year >= q.year & o.month >= q.month & o.day is null)
            #  | (o.year >= q.year & o.month >= q.month & o.day >= q.day)
            #
            # which equals:
            #  o.year >= q.year 
            #  & (o.month is null
            #    | (o.month >= q.month & o.day is null)
            #    | (o.month >= q.month & o.day >= q.day))
            #
            #  o.year >= q.year 
            #  & (o.month is null
            #    | (o.month >= q.month 
            #      & (o.day is null
            #        | o.day >= q.day)))
            
            date = form.cleaned_data['after_date']
            
            year_match = Q(observation__observation_datetime__year__gte=date.year)
            month_null = Q(observation__observation_datetime__month__isnull=True)
            month_match = Q(observation__observation_datetime__month__gte=date.month)
            day_null = Q(observation__observation_datetime__day__isnull=True)
            day_match = Q(observation__observation_datetime__day__gte=date.day)
            
            observation_date_match = (year_match 
                & (month_null
                    | (month_match
                        & (day_null
                            | day_match))))
            
            year_match = Q(observation__report_datetime__year__gte=date.year)
            month_null = Q(observation__report_datetime__month__isnull=True)
            month_match = Q(observation__report_datetime__month__gte=date.month)
            day_null = Q(observation__report_datetime__day__isnull=True)
            day_match = Q(observation__report_datetime__day__gte=date.day)
            
            report_date_match = (year_match 
                & (month_null
                    | (month_match
                        & (day_null
                            | day_match))))
            
            query &= (observation_date_match | report_date_match)

        if form.cleaned_data['before_date']:
            # same as above, but with 'lte' instead of 'gte'

            date = form.cleaned_data['before_date']

            year_match = Q(observation__observation_datetime__year__lte=date.year)
            month_null = Q(observation__observation_datetime__month__isnull=True)
            month_match = Q(observation__observation_datetime__month__lte=date.month)
            day_null = Q(observation__observation_datetime__day__isnull=True)
            day_match = Q(observation__observation_datetime__day__lte=date.day)
            
            observation_date_match = (year_match 
                & (month_null
                    | (month_match
                        & (day_null
                            | day_match))))
            
            year_match = Q(observation__report_datetime__year__lte=date.year)
            month_null = Q(observation__report_datetime__month__isnull=True)
            month_match = Q(observation__report_datetime__month__lte=date.month)
            day_null = Q(observation__report_datetime__day__isnull=True)
            day_match = Q(observation__report_datetime__day__lte=date.day)
            
            report_date_match = (year_match 
                & (month_null
                    | (month_match
                        & (day_null
                            | day_match))))
            
            query &= (observation_date_match | report_date_match)
        
        if form.cleaned_data['taxon']:
            t = form.cleaned_data['taxon']
            # TODO handle taxon uncertainty!
            query &= Q(observation__taxon__in=Taxon.objects.with_descendants(t))

        if form.cleaned_data['case_name']:
            name = form.cleaned_data['case_name']
            query &= Q(names__icontains=name)

        if form.cleaned_data['observation_narrative']:
            on = form.cleaned_data['observation_narrative']
            query &= Q(observation__narrative__icontains=on)

        # TODO shoulde be ordering such that cases with no date come first
        case_order_args = ('-current_yearnumber__year', '-current_yearnumber__number', 'id')

        # TODO Oracle doesn't support distinct() on models with TextFields
        #cases = manager.filter(query).distinct().order_by(*case_order_args)
        cases = manager.filter(query).order_by(*case_order_args)
        
        # simulate distinct() for Oracle
        # an OrderedSet in the collections library would be nice...
        # TODO not even a good workaround, since we have to pass in the count
        # seprately
        seen = set()
        case_list = list()
        for c in cases:
            if not c in seen:
                seen.add(c)
                case_list.append(c)

    return render_to_response(
        "incidents/case_search.html",
        {
            'form': form,
            'case_list': case_list,
            'case_count': len(case_list),
        },
        context_instance= RequestContext(request),
    )

