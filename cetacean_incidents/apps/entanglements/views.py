from datetime import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.db import transaction
from django.db import models
from django.conf import settings

from reversion import revision

from cetacean_incidents.apps.incidents.models import Case

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.uncertain_datetimes.forms import NiceDateTimeForm
from cetacean_incidents.apps.contacts.forms import ContactForm, OrganizationForm
from cetacean_incidents.apps.incidents.forms import AnimalForm

from cetacean_incidents.apps.incidents.views import case_detail, edit_case, add_observation, edit_observation

from models import Entanglement, GearType, EntanglementObservation, BodyLocation, GearBodyLocation
from forms import EntanglementForm, AddEntanglementForm, EntanglementObservationForm, GearOwnerForm

@login_required
def edit_entanglement(request, entanglement_id):
    return edit_case(
        request,
        case_id= Entanglement.objects.get(id=entanglement_id).case_ptr.id,
        template= 'entanglements/edit_entanglement.html', 
        form_class= EntanglementForm,
    )

@login_required
def add_gear_owner(request, entanglement_id):
    # TODO merge in with edit_gear_owner
    entanglement = Entanglement.objects.get(id=entanglement_id)

    form_classes = {
        'gear_owner': GearOwnerForm,
        'datetime_set': NiceDateTimeForm,
        'location_set': NiceLocationForm,
        'datetime_lost': NiceDateTimeForm,
    }
    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = {}
        if request.method == 'POST':
            kwargs['data'] = request.POST
        forms[form_name] = form_class(prefix=form_name, **kwargs)
            
    if request.method == 'POST':
        class _SomeValidationFailed(Exception):
            pass
        class _NothingToSave(Exception):
            pass
        def _check(form_name):
            if not forms[form_name].is_valid():
                raise _SomeValidationFailed(form_name, forms[form_name])

        # Revisions should always correspond to transactions!
        @transaction.commit_on_success
        @revision.create_on_success
        def _try_saving():
            _check('gear_owner')
            gear_owner = forms['gear_owner'].save()
            entanglement.gear_owner_info = gear_owner
            entanglement.save()
            
            if forms['gear_owner'].cleaned_data['date_set_known']:
                _check('datetime_set')
                gear_owner.date_gear_set = forms['datetime_set'].save()
            if forms['gear_owner'].cleaned_data['location_set_known']:
                _check('location_set')
                gear_owner.location_gear_set = forms['location_set'].save()
            if forms['gear_owner'].cleaned_data['date_lost_known']:
                _check('datetime_lost')
                gear_owner.date_gear_missing = forms['datetime_lost'].save()
            
            gear_owner.save()

            return entanglement

        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            print "error in form %s: %s" % (formname, unicode(form.errors))

    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js', 'checkboxhider.js'),
    )
    
    return render_to_response(
        'entanglements/add_gear_owner.html',
        {
            'case': entanglement,
            'forms': forms,
            'all_media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
def edit_gear_owner(request, entanglement_id):
    entanglement = Entanglement.objects.get(id=entanglement_id)
    gear_owner = entanglement.gear_owner_info

    form_classes = {
        'gear_owner': GearOwnerForm,
        'datetime_set': NiceDateTimeForm,
        'location_set': NiceLocationForm,
        'datetime_lost': NiceDateTimeForm,
    }

    form_initials = {
        'gear_owner': {
            'date_set_known': False,
            'date_lost_known': False,
        }
    }
    if gear_owner.date_gear_set:
        form_initials['gear_owner']['date_set_known'] = True
    if gear_owner.location_gear_set:
        form_initials['gear_owner']['location_set_known'] = True
    if gear_owner.date_gear_missing:
        form_initials['gear_owner']['date_lost_known'] = True

    model_instances = {
        'gear_owner': gear_owner,
        'datetime_set': gear_owner.date_gear_set,
        'location_set': gear_owner.location_gear_set,
        'datetime_lost': gear_owner.date_gear_missing,
    }

    forms = {}
    for form_name, form_class in form_classes.items():
        kwargs = {}
        if request.method == 'POST':
            kwargs['data'] = request.POST
        if form_name in model_instances.keys():
            kwargs['instance'] = model_instances[form_name]
        if form_name in form_initials.keys():
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
        
            _check('gear_owner')
            gear_owner = forms['gear_owner'].save()
            entanglement.gear_owner_info = gear_owner
            entanglement.save()
            
            if forms['gear_owner'].cleaned_data['date_set_known']:
                _check('datetime_set')
                gear_owner.date_gear_set = forms['datetime_set'].save()
            else:
                date_set = gear_owner.date_gear_set
                if not date_set is None:
                    gear_owner.date_gear_set = None
                    # be sure to remove the datetime reference from the 
                    # gear_owner and save, or else you'll delete the entire
                    # case!
                    gear_owner.save()
                    date_set.delete()
            
            if forms['gear_owner'].cleaned_data['location_set_known']:
                _check('location_set')
                gear_owner.location_gear_set = forms['location_set'].save()
            else:
                loc_set = gear_owner.location_gear_set
                if not loc_set is None:
                    gear_owner.location_gear_set = None
                    gear_owner.save()
                    loc_set.delete()

            if forms['gear_owner'].cleaned_data['date_lost_known']:
                _check('datetime_lost')
                gear_owner.date_gear_missing = forms['datetime_lost'].save()
            else:
                date_lost = gear_owner.date_gear_missing
                if not date_lost is None:
                    gear_owner.date_gear_missing = None
                    gear_owner.save()
                    date_lost.delete()
            
            gear_owner.save()
            
            return entanglement

        try:
            return redirect(_try_saving())
        except _SomeValidationFailed as (formname, form):
            print "error in form %s: %s" % (formname, unicode(form.errors))

    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js', 'checkboxhider.js'),
    )
    
    return render_to_response(
        'entanglements/edit_gear_owner.html',
        {
            'case': entanglement,
            'forms': forms,
            'all_media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@login_required
def entanglementobservation_detail(request, entanglementobservation_id):
    entanglementobservation = EntanglementObservation.objects.get(id=entanglementobservation_id)
    body_locations = []
    for loc in BodyLocation.objects.all():
        gear_loc = GearBodyLocation.objects.filter(observation=entanglementobservation, location=loc)
        if gear_loc.exists():
            body_locations.append((loc, gear_loc[0]))
        else:
            body_locations.append((loc, None))
    return render_to_response(
        'entanglements/entanglement_observation_detail.html',
        {
            'observation': entanglementobservation,
            'gear_body_locations': body_locations,
            'media': Media(js=(settings.JQUERY_FILE, 'radiohider.js')),
        },
        context_instance= RequestContext(request),
    )

@login_required
def add_entanglementobservation(request, animal_id=None, entanglement_id=None):
    return add_observation(
        request,
        animal_id= animal_id,
        case_id= entanglement_id,
        template= 'entanglements/add_entanglement_observation.html',
        observationform_class= EntanglementObservationForm,
        caseform_class= EntanglementForm,
        addcaseform_class= AddEntanglementForm,
    )

@login_required
def edit_entanglementobservation(request, entanglementobservation_id):
    return edit_observation(
        request,
        observation_id = entanglementobservation_id,
        template= 'entanglements/edit_entanglement_observation.html',
        observationform_class= EntanglementObservationForm,
        caseform_class= EntanglementForm,
    )

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
        'geartypes': modelformset_factory(GearType, extra=3)(),
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
            print "error in form %s: %s" % (formname, unicode(form.errors))

    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js'),
    )

    media = reduce(lambda x, y: x + y.media, forms.itervalues(), template_media)
    
    return render_to_response(
        'entanglements/entanglement_report_form.html',
        {
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

