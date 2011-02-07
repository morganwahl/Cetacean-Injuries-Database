import operator

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import Media
from django.forms.formsets import formset_factory
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from reversion import revision

from cetacean_incidents import generic_views
from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.contacts.forms import ContactForm, OrganizationForm

from cetacean_incidents.apps.locations.forms import NiceLocationForm

from cetacean_incidents.apps.vessels.forms import ObserverVesselInfoForm

from cetacean_incidents.apps.jquery_ui.tabs import Tab, Tabs

from ..models import Animal, Case
from ..forms import AnimalForm, AddCaseForm, CaseForm

from ..models import Observation, ObservationExtension
from ..forms import ObservationForm

from case import _make_animal_tabs, _make_case_tabs

@login_required
def observation_detail(request, observation_id):
    observation = Observation.objects.get(id=observation_id)
    extra_context = {
        'media': Media(js=(settings.JQUERY_FILE, 'radiohider.js')),
    }
    # TODO generify
    for oe_attr in (
        'entanglements_entanglementobservation', 
        'shipstrikes_shipstrikeobservation',
    ):
        if hasattr(observation, oe_attr):
            extra_context.update(getattr(observation, oe_attr)._extra_context)
    return generic_views.object_detail(
        request,
        object_id= observation_id,
        queryset= Observation.objects.all(),
        template_object_name= 'observation',
        extra_context= extra_context,
    )

# what this view does depends on a few things:
#  animal  case observation
#       *     *        True  edit obs. given and it's case and animal
#       *  True       False  add obs. to case given and edit case and case's animal
#    True False       False  new obs. and new case for animal given. edit animal too.
#   False False       False  new obs. of new animal with new case
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
        additional_tabs=[],
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
        # TODO some way of picking the case?
        case = observation.cases.all()[0].specific_instance()
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
    # for it. that would also make the page non-functional if we're adding a
    # new animal.
    if case is None:
        form_classes['case'] = addcaseform_class
    
    if request.user.has_perm('contacts.add_contact'):
        form_classes.update({
            'new_reporter': ContactForm,
            'new_observer': ContactForm,
            'new_vesselcontact': ContactForm,
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
        if sex:
            form_kwargs['observation']['initial']['gender'] = sex
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
        
        if 'observer_vessel' in model_instances and model_instances['observer_vessel'].contact:
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
        if not name in form_kwargs:
            form_kwargs[name] = {}
        if not 'initial' in form_kwargs[name]:
            form_kwargs[name]['initial'] = {}
        form_kwargs[name]['initial'].update(initials)
        
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
        
        # Revisions should always correspond to transactions!
        # Note that the TransactionMiddleware won't help us here, because the
        # view doesn't throw an exception if there's an error.
        @transaction.commit_on_success
        @revision.create_on_success
        def _try_saving():
            _check('animal')
            if not 'animal' in model_instances:
                animal = forms['animal'].save()
            else:
                animal = forms['animal'].save()
            
            _check('case')
            if not 'case' in model_instances:
                case = forms['case'].save(commit=False)
                # TODO move this to AddCaseForm.save?
                case.animal = animal
                case.save()
                forms['case'].save_m2m()
            else:
                case = forms['case'].save()
            
            _check('observation')
            if not 'observation' in model_instances: # if this is a new obs.
                observation = forms['observation'].save(commit=False)
                # TODO move this to ObservationForm.save?
                observation.animal = case.animal
                observation.save()
                forms['observation'].save_m2m()
                observation.cases.add(case)
            else: # we're just editing this obs
                observation = forms['observation'].save()
                observation.animal = case.animal # in case case.animal changed
                observation.save()
            
            if request.user.has_perm('contacts.add_contact'):
                if forms['observation'].cleaned_data['new_reporter'] == 'new':
                    _check('new_reporter')
                    observation.reporter = forms['new_reporter'].save()
                    observation.save()
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
            
            return observation

        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            #print "error in form %s: %s" % (formname, unicode(form.errors))
            pass
    
    context = RequestContext(request, {
        'animal': animal,
        'case': case,
        'observation': observation,
        'forms': forms,
    })
    
    template_media = Media(
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'radiohider.js', 'checkboxhider.js', 'selecthider.js'),
    )
    
    tabs = Tabs(_make_animal_tabs(animal, forms['animal']) + _make_case_tabs(case, forms['case']) + [
         Tab(
            html_id= 'observation-reporting',
            template= get_template('incidents/edit_observation_reporting_tab.html'),
            context= context,
            html_display= mark_safe(u"<em>Observation</em><br>Reporter"),
            error= reduce(operator.or_, map(
                bool,
                [
                    forms['observation'].non_field_errors(),
                    forms['new_reporter'].errors,
                ] + forms['new_reporter_affiliations'].errors + map(
                    lambda f: forms['observation'][f].errors, 
                    (
                        'datetime_reported',
                        'new_reporter',
                        'reporter',
                    ),
                ),
            )),
         ),
         Tab(
            html_id= 'observation-observing',
            template= get_template('incidents/edit_observation_observing_tab.html'),
            context= context,
            html_display= mark_safe(u"<em>Observation</em><br>Observer"),
            error= reduce(operator.or_, map(
                bool,
                [
                    forms['observation'].non_field_errors(),
                    forms['new_observer'].errors,
                    forms['location'].errors,
                    forms['observer_vessel'].errors,
                    forms['new_vesselcontact'].errors,
                ] + forms['new_observer_affiliations'].errors + forms['new_vesselcontact_affiliations'].errors + map(
                    lambda f: forms['observation'][f].errors, 
                    (
                        'initial',
                        'exam',
                        'datetime_observed',
                        'new_observer',
                        'observer',
                        'observer_on_vessel',
                    ),
                ),
            )),
         ),
         Tab(
            html_id= 'observation-animal_identification',
            template= get_template('incidents/edit_observation_animal_identification_tab.html'),
            context= context,
            html_display= mark_safe(u"<em>Observation</em><br>Animal Identification"),
            error= reduce(operator.or_, map(
                bool,
                [
                    forms['observation'].non_field_errors(),
                ] + map(
                    lambda f: forms['observation'][f].errors, 
                    (
                        'taxon',
                        'gender',
                        'animal_description',
                        'age_class',
                        'condition',
                        'biopsy',
                        'genetic_sample',
                        'tagged',
                    ),
                ),
            )),
         ),
         Tab(
            html_id= 'observation-incident',
            template= get_template('incidents/edit_observation_incident_tab.html'),
            context= context,
            html_display= mark_safe(u"<em>Observation</em><br>Incident"),
            error= reduce(operator.or_, map(
                bool,
                [
                    forms['observation'].non_field_errors(),
                ] + map(
                    lambda f: forms['observation'][f].errors, 
                    (
                        'documentation',
                        'ashore',
                        'wounded',
                        'wound_description',
                    ),
                ),
            )),
         ),
         Tab(
            html_id= 'observation-narrative',
            template= get_template('incidents/edit_observation_narrative_tab.html'),
            context= context,
            html_display= mark_safe(u"<em>Observation</em><br>Narrative"),
            error= reduce(operator.or_, map(
                bool,
                [
                    forms['observation'].non_field_errors(),
                ] + map(
                    lambda f: forms['observation'][f].errors, 
                    (
                        'narrative',
                    ),
                ),
            )),
        ),
    ] + additional_tabs
    )

    return render_to_response(
        template,
        {
            'tabs': tabs,
            'media': reduce( lambda m, f: m + f.media, forms.values() + [tabs], template_media),
        },
        context_instance= context,
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
    
