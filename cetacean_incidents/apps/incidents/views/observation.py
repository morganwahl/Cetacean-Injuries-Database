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

from ..models import Animal, Case
from ..forms import AnimalForm, AddCaseForm, CaseForm

from ..models import Observation
from ..forms import ObservationForm

@login_required
def observation_detail(request, observation_id):
    observation = Observation.objects.get(id=observation_id).specific_instance()
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

# what this view does depends on a few things:
#  animal_id case_id observation_id
#          *       *           True  edit obs. given and it's case and animal
#          *    True          False  add obs. to case given and edit case and case's animal
#      True    False          False  new obs. and new case for animal given. edit animal too.
#      False   False          False  new obs. of new animal with new case
def _change_incident(
        request,
        animal_id=None,
        case_id=None,
        observation_id=None,
        template='incidents/add_observation.html',
        caseform_class= CaseForm,
        addcaseform_class= AddCaseForm,
        observationform_class= ObservationForm,
        additional_form_classes= {},
        additional_model_instances = {},
        additional_form_initials= {},
        additional_form_saving= lambda forms, instances, check, observation: None,
    ):
    '''\
    The doomsday form-view. If case_id is not None, animal_id is ignored (the
    case's animal is used instead). If case_id is None, a new Case is created
    for the animal given in animal_id. If animal_id is None, a new Animal is
    added as well.
    
    observationform_class, if given, should be a subclass of ObservationForm.
    addcaseform_class should be the same as caseform_class, but without an
    animal field. additional_model_instances should have keys that correspond to
    the ones in additional_form_classes.
    '''
    
    ### First, we get all the model instances we'll want to edit
    
    # these are just shortcuts for model_instances['animal', 'case', 'observation']
    observation = None
    case = None
    animal = None
    if not observation_id is None: # not a new observation
        observation = Observation.objects.get(id=observation_id).specific_instance()
        case = observation.case.specific_instance()
        animal = observation.animal
    elif not case_id is None:
        case = Case.objects.get(id=case_id).specific_instance()
        animal = case.animal
    elif not animal_id is None:
        animal = Animal.objects.get(id=animal_id)
    
    model_instances = {}
    if animal:
        model_instances['animal'] = animal
    if case:
        model_instances['case'] = case
    if observation:
        model_instances['observation'] = observation
        if observation.observer_vessel:
            model_instances['observer_vessel'] = observation.observer_vessel
        if observation.location:
            model_instances['location'] = observation.location
    model_instances.update(additional_model_instances)

    ### Next we set up the dict of form classes

    form_classes = {
        'animal': AnimalForm,
        'case': caseform_class,
        'observation': observationform_class,
        'location': NiceLocationForm,
        'observer_vessel': ObserverVesselInfoForm,
    }
    
    # if we're adding a new case, there's no point in having an animal field
    # for it. that would also makes the page non-functional if we're adding a
    # new animal.
    if case is None:
        form_classes['case'] = addcaseform_class
    
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
    
    ### Now, we set up the dictionary of arguments used when instantiating the
    ### forms.
    
    form_kwargs = {}
    
    # 'prefix', 'instance', and 'data' args
    for name in form_classes.keys():
        form_kwargs[name] = {'prefix': name}
        if name in model_instances.keys():
            form_kwargs[name]['instance'] = model_instances[name]
        if request.method == 'POST':
            form_kwargs[name]['data'] = request.POST
    
    # 'initial' arg
    # TODO doesn't this belong in ObservationForm.__init__ ?
    if animal:
        taxon = animal.taxon()
        sex = animal.gender()
        if taxon or sex:
            if not 'initial' in form_kwargs['observation']:
                form_kwargs['observation']['initial'] = {}
        if taxon:
            form_kwargs['observation']['initial']['taxon'] = taxon
        if gender:
            form_kwargs['observation']['initial']['gender'] = gender
    if observation:
        if not 'initial' in form_kwargs['observation']:
            form_kwargs['observation']['initial'] = {}
        form_kwargs['observation']['initial']['observer_on_vessel'] = bool(observation.observer_vessel)
        if observation.reporter:
            form_kwargs['observation']['initial']['new_reporter'] = 'other'
        if observation.observer:
            # This causes unexpected behaviour when one sets 'new_reporter' to 
            # 'none'
            #if observation.observer == observation.reporter:
            #    form_kwargs['observation']['initial']['new_observer'] = 'reporter'
            #else:
                form_kwargs['observation']['initial']['new_observer'] = 'other'
        
        if model_instances['observer_vessel'] and model_instances['observer_vessel'].contact:
            # This causes unexpected behaviour when one sets 'new_reporter' to 
            # 'none'
            #if model_instances['observer_vessel'].contact == observation.reporter:
            #    form_kwargs['observer_vessel']['initial']['contact_choice'] = 'reporter'
            #if model_instances['observer_vessel'].contact == observation.observer:
            #    form_kwargs['observer_vessel']['initial']['contact_choice'] = 'observer'
            #else:
                form_kwargs['observer_vessel']['initial']['contact_choice'] = 'other'
                form_kwargs['observer_vessel']['initial']['existing_contact'] = model_instances['observer_vessel'].contact.id
    
    for name, initials in additional_form_initials.items():
        if name in form_kwargs and 'initial' in form_kwargs[name]:
            form_kwargs[form_name]['initial'].update(initials)
        else:
            form_kwargs[form_name]['initial'] = initials
    
    ### Finally, we instantiate the forms
    forms = {}
    for name, cls in form_classes.items():
        forms[name] = cls(**form_kwargs[name])
    
    ### Now, to actually process the forms if we got a POST
    if request.method == 'POST':
        class _SomeValidationFailed(Exception):
            pass
        def _check(form_name):
            if not forms[form_name].is_valid():
                raise _SomeValidationFailed(form_name, forms[form_name])
        
        # don't worry about saving some models and not others. The transaction
        # middleware will rollback any changes if an exception occurs
        def _try_saving():
            _check('animal')
            if not 'animal' in model_instances:
                animal = forms['animal'].save()
            else:
                forms['animal'].save()
            
            _check('case')
            if not 'case' in model_instances:
                case = forms['case'].save(commit=False)
                # TODO move this to AddCaseForm.save?
                case.animal = animal
                case.save()
                forms['case'].save_m2m()
            else:
                forms['case'].save()
            
            _check('observation')
            if not 'observation' in model_instances: # if this is a new obs.
                observation = forms['observation'].save(commit=False)
                # TODO move this to ObservationForm.save?
                observation.case = case
                observation.save()
                forms['observation'].save_m2m()
            else: # we're just editing this obs
                observation = forms['observation'].save()
            
            if request.user.has_perm('contacts.add_contact'):
                if forms['observation'].cleaned_data['new_reporter'] == 'new':
                    _check('new_reporter')
                    observation.reporter = forms['new_reporter'].save()
                    observation.save()
                    if request.user.has_perm('contacts.add_organization'):
                        _check('new_reporter_affiliations')
                        # TODO move this to the ContactForm
                        # add the affiliations from the new_affs_formset
                        for org_form in forms['new_reporter_affiliations'].forms:
                            # don't save orgs with blank names.
                            if not 'name' in org_form.cleaned_data:
                                continue
                            org = org_form.save()
                            observation.reporter.affiliations.add(org)
            if forms['observation'].cleaned_data['new_reporter'] == 'none':
                observation.reporter = None
                observation.save()
    
            _check('location')
            if not 'location' in model_instances:
                observation.location = forms['location'].save()
                observation.save()
            else:
                forms['location'].save()
            
            if request.user.has_perm('contacts.add_contact'):
                if forms['observation'].cleaned_data['new_observer'] == 'new':
                    _check('new_observer')
                    observation.observer = forms['new_observer'].save()
                    observation.save()
                    if request.user.has_perm('contacts.add_organization'):
                        _check('new_observer_affiliations')
                        # TODO move this to the ContactForm
                        # add the affiliations from the new_affs_formset
                        for org_form in forms['new_observer_affiliations'].forms:
                            # don't save orgs with blank names.
                            if not 'name' in org_form.cleaned_data:
                                continue
                            # check if maybe the new org was mentioned in a 
                            # previously processed new_aff_formset
                            org_query = Organization.objects.filter(name=org_form.cleaned_data['name'])
                            if org_query.count():
                                org = org_query[0] # orgs shouldn't really have 
                                                   # identical names anyway, so 
                                                   # just use the first one.
                            else:
                                org = org_form.save()
                            observation.observer.affiliations.add(org)
            if forms['observation'].cleaned_data['new_observer'] == 'reporter':
                observation.observer = observation.reporter
                observation.save()
            if forms['observation'].cleaned_data['new_observer'] == 'none':
                observation.observer = None
                observation.save()
            
            if forms['observation'].cleaned_data['observer_on_vessel'] == False:
                vessel_info = observation.observer_vessel
                observation.observer_vessel = None
                observation.save()
                if vessel_info: # be sure to only delete _after_ you've unhooked
                                # it from the observation
                    vessel_info.delete()
            else: # there's observer_vessel data
                _check('observer_vessel')
                if not 'observer_vessel' in model_instances:
                    observation.observer_vessel = forms['observer_vessel'].save()
                    observation.save()
                else:
                    forms['observation_vessel'].save()
                if request.user.has_perm('contacts.add_contact'):
                    if forms['observer_vessel'].cleaned_data['contact_choice'] == 'new':
                        _check('new_vesselcontact')
                        observation.observer_vessel.contact = forms['new_vesselcontact'].save()
                        observation.observer_vessel.save()
                        if request.user.has_perm('contacts.add_organization'):
                            _check('new_vesselcontact_affiliations')
                            # add the affiliations from the new_affs_formset
                            for org_form in forms['new_vesselcontact_affiliations'].forms:
                                # don't save orgs with blank names.
                                if not 'name' in org_form.cleaned_data:
                                    continue
                                # check if maybe the new org was mentioned in a 
                                # previously processed new_aff_formset
                                org_query = Organization.objects.filter(name=org_form.cleaned_data['name'])
                                if org_query.count():
                                    org = org_query[0] # orgs shouldn't really
                                                       # have identical names 
                                                       # anyway, so just use the 
                                                       # first one.
                                else:
                                    org = org_form.save()
                                observation.observer_vessel.contact.affiliations.add(org)
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
                    observation.observer_vessel.contact = observation.reporter
                    observation.observer_vessel.save()
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'observer':
                    observation.observer_vessel.contact = observation.observer
                    observation.observer_vessel.save()
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'other':
                    observation.observer_vessel.contact = forms['observer_vessel'].cleaned_data['existing_contact']
                    observation.observer_vessel.save()
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'none':
                    observation.observer_vessel.contact = None
                    observation.observer_vessel.save()

            additional_form_saving(forms, model_instances, _check, observation)

        try:
            _try_saving()
            return redirect(observation)
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
            'observation': observation,
            'forms': forms,
            'media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

# TODO rename, since it also can add animals and cases
# TODO split out into wrapper functions to check for correct add/change_animal
# permissions
@login_required
@permission_required('incidents.add_observation')
@permission_required('incidents.add_case')
@permission_required('incidents.change_case')
def add_observation(request, animal_id=None, case_id=None):
    
    return _change_incident(request, animal_id=animal_id, case_id=case_id)
    
@login_required
@permission_required('incidents.change_observation')
@permission_required('incidents.change_case')
@permission_required('incidents.change_animal')
def edit_observation(request, observation_id):
    
    return _change_incident(request, observation_id=observation_id)
    
