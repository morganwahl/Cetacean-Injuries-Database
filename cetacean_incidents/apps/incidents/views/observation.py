import operator

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import Media
from django.forms.formsets import formset_factory
from django.shortcuts import render_to_response, redirect
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from reversion import revision

from cetacean_incidents import generic_views
from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.contacts.forms import ContactForm, OrganizationForm

from cetacean_incidents.apps.locations.forms import NiceLocationForm

from cetacean_incidents.apps.vessels.forms import VesselInfoForm

from cetacean_incidents.apps.jquery_ui.tabs import Tabs

from ..models import Animal, Case
from ..forms import AnimalForm, AddCaseForm, CaseForm

from ..models import Observation, ObservationExtension
from ..forms import ObservationForm, ObservationCasesForm

from tabs import AnimalTab, CaseTab, CaseSINMDTab, ObservationReportingTab, ObservationObservingTab, ObservationAnimalIDTab, ObservationIncidentTab, ObservationNarrativeTab

@login_required
def observation_detail(request, observation_id):
    observation = Observation.objects.get(id=observation_id)
    
    show_cases_form = False
    if request.method == 'POST':
        cases_form = ObservationCasesForm(observation, data=request.POST)
        if cases_form.is_valid():
            new_cases = set(cases_form.cleaned_data['cases'])
            old_cases = set(observation.cases.all())
            if new_cases != old_cases:
                observation.cases = new_cases
        else: # there was an error with the form
            show_cases_form = True
    else:
        cases_form = ObservationCasesForm(observation)
    
    extra_context = {
        'media': Media(js=(settings.JQUERY_FILE, 'radiohider.js')),
        'show_cases_form': show_cases_form,
        'cases_form': cases_form,
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
#  animal  cases observation
#       *      *        True  edit obs. given and it's cases and animal
#       *   True       False  add obs. to cases given and edit those cases and their animal
#    True  False       False  new obs. and new case for animal given. edit animal too.
#   False  False       False  new obs. of new animal with new case
def _change_incident(
        request,
        animal=None,
        cases=None,
        new_case_form_class=AddCaseForm,
        observation=None,
        template='incidents/add_observation.html',
        additional_form_classes= {},
        additional_form_initials= {},
        additional_model_instances = {},
        additional_form_saving= lambda forms, instances, check, observation: None,
        additional_case_tabs=[], # should be a list of lists with additional tabs for each case
        additional_observation_tabs=[],
        additional_tab_context={},
    ):
    '''\
    The doomsday form-view. If case is not None, animal is ignored (the case's
    animal is used instead). If case is None, a new Case is created for the
    animal given. If animal is None, a new Animal is added as well.
    
    additional_model_instances should have keys that correspond to
    the ones in additional_form_classes.
    '''
    
    if not observation is None: # not a new observation
        # TODO some way of picking the case?
        cases = [c.specific_instance() for c in observation.cases.all()]
        animal = observation.animal
    elif not cases is None:
        animal = cases[0].animal
    
    if not cases is None:
        # check that all the cases have 'animal' as their animal
        for c in cases:
            if c.animal != animal:
                raise ValueError("These cases are for different animals!")
    
    def _case_key(case):
        return 'case-' + unicode(c.pk) 

    ### First, we get all the model instances we'll want to edit
    # note that 'animal', 'cases', and 'observation' are just shortcuts. all the
    # instance we want to edit are in model_instances
    model_instances = {}
    if animal:
        model_instances['animal'] = animal
    if cases:
        for c in cases:
            model_instances[_case_key(c)] = c
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
        'observation': ObservationForm,
        'location': NiceLocationForm,
        'observer_vessel': VesselInfoForm,
    }
    if cases: # we're editing cases
        for c in cases:
            form_classes[_case_key(c)] = c.form_class
    else: # we're adding cases
        form_classes['new_case'] = new_case_form_class
    
    if request.user.has_perm('contacts.add_contact'):
        form_classes.update({
            'new_reporter': ContactForm,
            'new_observer': ContactForm,
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
            valid = forms[form_name].is_valid()
            if not valid:
                #print "got validity: %s" % repr(valid)
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
            
            if cases: # we're editing existing cases
                for c in cases:
                    k = _case_key(c)
                    _check(k)
                    forms[k].save()
            else: # we're adding a new case
                _check('new_case')
                new_case = forms['new_case'].save(commit=False)
                # TODO move this to AddCaseForm.save?
                new_case.animal = animal
                new_case.save()
                forms['new_case'].save_m2m()
        
            _check('observation')
            if not 'observation' in model_instances: # if this is a new obs.
                observation = forms['observation'].save(commit=False)
                # TODO move this to ObservationForm.save?
                observation.animal = animal
                observation.save()
                forms['observation'].save_m2m()
                if cases: # we're editing existing cases
                    for c in cases:
                        observation.cases.add(c)
                else: # we're adding a new case
                    observation.cases.add(new_case)
            else: # we're just editing this obs
                observation = forms['observation'].save()
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
                    forms['observer_vessel'].save()
                if forms['observer_vessel'].cleaned_data['contact_choice'] == 'reporter':
                    observation.observer_vessel.contact = observation.reporter
                    observation.observer_vessel.save()
                elif forms['observer_vessel'].cleaned_data['contact_choice'] == 'observer':
                    observation.observer_vessel.contact = observation.observer
                    observation.observer_vessel.save()
                # 'new', 'other', and 'none' are handled by VesselInfoForm.save

            additional_form_saving(forms, model_instances, _check, observation)
            
            return observation

        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            #print "error in form %s: %s" % (formname, unicode(repr(form.errors)))
            pass
    
    tab_context = RequestContext(request, {
        'animal': animal,
        'animal_form': forms['animal'],
        'cases': cases,
        'observation': observation,
        'forms': forms,
    })
    tab_context.update(additional_tab_context)
    
    animal_tabs = [AnimalTab(context=tab_context)]

    if cases: # we're editing existing cases
        case_tabs = []
        for i in range(len(cases)):
            c = cases[i]
            k = _case_key(c)
            case_tab_context = RequestContext(request, {
                'case': c,
                'case_form': forms[k],
            })
            
            try:
                additional_tabs = additional_case_tabs[i]
            except IndexError:
                additional_tabs = []
            if hasattr(c, 'extra_tab_class'):
                additional_tabs = [c.extra_tab_class()] + additional_tabs
            for t in additional_tabs:
                t.context = case_tab_context
                t.html_id = k + '-' + t.html_id

            these_case_tabs = [
                CaseTab(html_id=k + '-case', context=case_tab_context),
                CaseSINMDTab(html_id=k + '-case-sinmd', context=case_tab_context),
            ] + additional_tabs
            
            case_tabs += these_case_tabs
    else: # we're adding a new case
        case_tab_context = RequestContext(request, {
            'case': None,
            'case_form': forms['new_case'],
        })
        case_tabs = [
            CaseTab(html_id='new_case', context=case_tab_context),
            CaseSINMDTab(html_id='new_case-sinmd', context=case_tab_context),
        ]
        
    observation_tabs = [
        ObservationReportingTab(html_id='observation-reporting'),
        ObservationObservingTab(html_id='observation-observing'),
        ObservationAnimalIDTab(html_id='observation-animal'),
        ObservationIncidentTab(html_id='observation-incident'),
    ] + additional_observation_tabs +[
        ObservationNarrativeTab(html_id='observation-narrative'),
    ]
    for t in observation_tabs:
        t.context = tab_context
    
    tabs = Tabs(animal_tabs + case_tabs + observation_tabs)

    template_media = Media(
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE, 'radiohider.js', 'checkboxhider.js', 'selecthider.js'),
    )
    
    return render_to_response(
        template,
        {
            'tabs': tabs,
            'media': reduce( lambda m, f: m + f.media, forms.values() + [tabs], template_media),
        },
        context_instance= tab_context,
    )

# TODO rename, since it also can add animals and cases
# TODO split out into wrapper functions to check for correct add/change_animal
# permissions
@login_required
@permission_required('incidents.add_observation')
@permission_required('incidents.add_case')
@permission_required('incidents.change_case')
def add_observation(request, animal_id=None, case_id=None):
    '''\
    Create a new observation with no ObservationExtensions and attach it to
    a regular Case, creating the Case if necessary.
    
    If a case_id is given, that case's animal will be used and animal_id will
    be ignored.
    '''
    
    animal = None
    cases = None
    if not case_id is None:
        cases = [Case.objects.get(id=case_id)]
        animal = case.animal
    elif not animal_id is None:
        animal = Animal.objects.get(id=animal_id)
    
    return _change_incident(request, animal=animal, cases=cases)
    
@login_required
@permission_required('incidents.change_observation')
@permission_required('incidents.change_case')
@permission_required('incidents.change_animal')
def edit_observation(request, observation_id):
    
    observation = Observation.objects.get(id=observation_id)

    extensions = observation.get_observation_extensions()
    # TODO there must be a better way just putting all this view data on the 
    # ObservationExtension models...
    form_classes = {}
    form_initials = {}
    model_instances = {}
    form_saving_funcs = []
    tabs = []
    for e in extensions:
        d = e.get_observation_view_data()
        if 'form_classes' in d:
            form_classes.update(d['form_classes'])
        if 'form_initials' in d:
            form_initials.update(d['form_initials'])
        if 'model_instances' in d:
            model_instances.update(d['model_instances'])
        if 'form_saving' in d:
            form_saving_funcs.append(d['form_saving'])
        if 'tabs' in d:
            tabs += d['tabs']
    
    def saving(*args, **kwargs):
        for func in form_saving_funcs:
            func(*args, **kwargs)
    
    return _change_incident(
        request, 
        observation= observation,
        additional_form_classes= form_classes,
        additional_form_initials= form_initials,
        additional_model_instances= model_instances,
        additional_form_saving= saving,
        additional_observation_tabs= tabs,
    )

