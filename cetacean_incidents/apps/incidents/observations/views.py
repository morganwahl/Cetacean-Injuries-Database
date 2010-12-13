from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import Media
from django.forms.formsets import formset_factory
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from reversion import revision

from cetacean_incidents import generic_views
from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.contacts.forms import ContactForm, OrganizationForm

from cetacean_incidents.apps.locations.forms import NiceLocationForm

from cetacean_incidents.apps.vessels.forms import ObserverVesselInfoForm

from cetacean_incidents.apps.documents.views import _get_documentforms, _save_documentforms

from ..models import Animal, Case
from ..forms import AnimalForm, AddCaseForm, CaseForm

from ..models import Observation, ObservationDocument
from ..forms import ObservationForm

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
        extra_context= {
            'media': Media(js=(settings.JQUERY_FILE, 'radiohider.js')),
        }
    )

# TODO merge add_observation and change_observation
# TODO rename, since it also can add animals and cases
# TODO split out into wrapper functions to check for correct add/change_animal
# permissions
@login_required
@permission_required('incidents.add_observation')
@permission_required('incidents.add_case')
@permission_required('incidents.change_case')
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
    The doomsday form-view. If case_id is not None, animal_id is ignored (the
    case's animal is used instead). If case_id is None, a new Case is created
    for the animal given in animal_id. If animal_id is None, a new Animal is
    added as well.
    
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
        'location': NiceLocationForm,
        'observer_vessel': ObserverVesselInfoForm,
    }
    if request.user.has_perm('contacts.add_contact'):
        form_classes.update({
            'new_reporter': ContactForm,
            'new_observer': ContactForm,
            'new_vesselcontact': ContactForm,
        })
        if request.user.has_perm('contacts.add_organization'):
            form_classes.update({
                'new_reporter_affiliations': formset_factory(OrganizationForm, extra=2),
                'new_observer_affiliations': formset_factory(OrganizationForm, extra=2),
                'new_vesselcontact_affiliations': formset_factory(OrganizationForm, extra=2),
            })
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
            
            if request.user.has_perm('contacts.add_contact'):
                if forms['observation'].cleaned_data['new_reporter'] == 'new':
                    _check('new_reporter')
                    if request.user.has_perm('contacts.add_organization'):
                        _check('new_reporter_affiliations')
                    observation.reporter = forms['new_reporter'].save()
                    if request.user.has_perm('contacts.add_organization'):
                        # add the affiliations from the new_affs_formset
                        for org_form in forms['new_reporter_affiliations'].forms:
                            # don't save orgs with blank names.
                            if not 'name' in org_form.cleaned_data:
                                continue
                            org = org_form.save()
                            observation.reporter.affiliations.add(org)
            
            _check('location')
            observation.location = forms['location'].save()
            
            if request.user.has_perm('contacts.add_contact'):
                if forms['observation'].cleaned_data['new_observer'] == 'new':
                    _check('new_observer')
                    if request.user.has_perm('contacts.add_organization'):
                        _check('new_observer_affiliations')
                    observation.observer = forms['new_observer'].save()
                    if request.user.has_perm('contacts.add_organization'):
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
            if forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
            
            if forms['observation'].cleaned_data['observer_on_vessel'] == True:
                _check('observer_vessel')
                observer_vessel = forms['observer_vessel'].save(commit=False)
                if request.user.has_perm('contacts.add_contact'):
                    if forms['observer_vessel'].cleaned_data['contact_choice'] == 'new':
                        _check('new_vesselcontact')
                        if request.user.has_perm('contacts.add_organization'):
                            _check('new_vesselcontact_affiliations')
                        observer_vessel.contact = forms['new_vesselcontact'].save()
                        if request.user.has_perm('contacts.add_organization'):
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
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
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
            #print "error in form %s: %s" % (formname, unicode(form.errors))
            pass

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
@permission_required('incidents.change_observation')
@permission_required('incidents.change_case')
@permission_required('incidents.change_animal')
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
        'location': NiceLocationForm,
        'observer_vessel': ObserverVesselInfoForm,
    }
    if request.user.has_perm('contacts.add_contact'):
        form_classes.update({
            'new_reporter': ContactForm,
            'new_observer': ContactForm,
            'new_vesselcontact': ContactForm,
        })
        if request.user.has_perm('contact.add_organization'):
            form_classes.update({
                'new_reporter_affiliations': formset_factory(OrganizationForm, extra=2),
                'new_observer_affiliations': formset_factory(OrganizationForm, extra=2),
                'new_vesselcontact_affiliations': formset_factory(OrganizationForm, extra=2),
            })
    form_classes.update(additional_form_classes)
    
    observation = Observation.objects.get(id=observation_id).detailed
    case = observation.case.detailed
    animal = case.animal

    model_instances = {
        'animal': observation.case.animal,
        'case': observation.case,
        'observation': observation,
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
        # This causes unexpected behaviour when one sets 'new_reporter' to 'none'
        #if model_instances['observation'].observer == model_instances['observation'].reporter:
        #    form_initials['observation']['new_observer'] = 'reporter'
        #else:
            form_initials['observation']['new_observer'] = 'other'

    if model_instances['observer_vessel'] and model_instances['observer_vessel'].contact:
        # This causes unexpected behaviour when one sets 'new_reporter' to 'none'
        #if model_instances['observer_vessel'].contact == model_instances['observation'].reporter:
        #    form_initials['observer_vessel']['contact_choice'] = 'reporter'
        #if model_instances['observer_vessel'].contact == model_instances['observation'].observer:
        #    form_initials['observer_vessel']['contact_choice'] = 'observer'
        #else:
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
            
            if request.user.has_perm('contacts.add_contact'):
                if forms['observation'].cleaned_data['new_reporter'] == 'new':
                    _check('new_reporter')
                    if request.user.has_perm('contacts.add_organization'):
                        _check('new_reporter_affiliations')
                    observation.reporter = forms['new_reporter'].save()
                    if request.user.has_perm('contacts.add_organization'):
                        # add the affiliations from the new_affs_formset
                        for org_form in forms['new_reporter_affiliations'].forms:
                            # don't save orgs with blank names.
                            if not 'name' in org_form.cleaned_data:
                                continue
                            org = org_form.save()
                            observation.reporter.affiliations.add(org)
            if forms['observation'].cleaned_data['new_reporter'] == 'none':
                observation.reporter = None
            
            _check('location')
            observation.location = forms['location'].save()
            
            if request.user.has_perm('contacts.add_contact'):
                if forms['observation'].cleaned_data['new_observer'] == 'new':
                    _check('new_observer')
                    if request.user.has_perm('contacts.add_organization'):
                        _check('new_observer_affiliations')
                    observation.observer = forms['new_observer'].save()
                    if request.user.has_perm('contacts.add_organization'):
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
            if forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
            if forms['observation'].cleaned_data['new_observer'] == 'none':
                observation.observer = None
            
            if forms['observation'].cleaned_data['observer_on_vessel'] == True:
                _check('observer_vessel')
                observer_vessel = forms['observer_vessel'].save(commit=False)
                if request.user.has_perm('contacts.add_contact'):
                    if forms['observer_vessel'].cleaned_data['contact_choice'] == 'new':
                        _check('new_vesselcontact')
                        if request.user.has_perm('contacts.add_organization'):
                            _check('new_vesselcontact_affiliations')
                        observer_vessel.contact = forms['new_vesselcontact'].save()
                        if request.user.has_perm('contacts.add_organization'):
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
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
                    observer_vessel.contact = observation.reporter
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'observer':
                    observer_vessel.contact = observation.observer
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'other':
                    observer_vessel.contact = forms['observer_vessel'].cleaned_data['existing_contact']
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'none':
                    observer_vessel.contact = None
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
@permission_required('documents.add_document')
def add_observationdocument(request, observation_id):
    
    o = Observation.objects.get(id=observation_id)
    
    forms = _get_documentforms(request)
    
    if request.method == 'POST':
        doc = _save_documentforms(request, forms)
        if doc:
            obs_doc = ObservationDocument.objects.create(
                document= doc,
                attached_to= o,
            )
            return redirect(o)
    
    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js'),
    )
    media = reduce( lambda m, f: m + f.media, forms.values(), template_media)
    
    return render_to_response(
        'incidents/add_observationdocument.html',
        {
            'observation': o,
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

