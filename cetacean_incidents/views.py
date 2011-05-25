from difflib import SequenceMatcher

import json

import numbers

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.urlresolvers import NoReverseMatch
from django.forms import Media
from django.http import HttpResponse
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import RequestContext
from django.utils.safestring import mark_safe

from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.contrib.contenttypes.models import ContentType

from reversion.models import (
    Revision,
    Version,
)

from decorators import permission_required
from forms import (
    AnimalChoiceForm,
    CaseTypeForm_factory,
)

from cetacean_incidents.apps.contacts.models import (
    Contact,
    Organization,
)

from cetacean_incidents.apps.entanglements.forms import (
    AnimalNMFSIDLookupForm,
    EntanglementNMFSIDLookupForm,
)
from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.entanglements.views import add_entanglementobservation

from cetacean_incidents.apps.incidents.forms import (
    AnimalIDLookupForm,
    AnimalFieldNumberLookupForm,
    AnimalSearchForm,
    CaseIDLookupForm,
    CaseYearlyNumberLookupForm,
    CaseSearchForm,
)
from cetacean_incidents.apps.incidents.models import (
    Animal,
    Case,
    Observation,
    YearCaseNumber,
)
from cetacean_incidents.apps.incidents.views import add_observation

from cetacean_incidents.apps.shipstrikes.models import Shipstrike
from cetacean_incidents.apps.shipstrikes.views import add_shipstrikeobservation

from cetacean_incidents.apps.taxons.views import import_search as unsecured_import_taxon

@login_required
def home(request):
    form_classes = {
        'animal_lookup_id': AnimalIDLookupForm,
        'animal_lookup_nmfs': AnimalNMFSIDLookupForm,
        'animal_lookup_field_number': AnimalFieldNumberLookupForm,
        'case_lookup_id': CaseIDLookupForm,
        'case_lookup_yearlynumber': CaseYearlyNumberLookupForm,
        'entanglement_lookup_nmfs': EntanglementNMFSIDLookupForm,
        'animal_search': AnimalSearchForm,
        'case_search': CaseSearchForm,
    }
    forms = {}
    for (form_name, form_class) in form_classes.items():
        kwargs = {}
        if request.method == 'GET':
            if '%s-submitted' % form_name in request.GET:
                kwargs['data'] = request.GET
        forms[form_name] = form_class(prefix=form_name, **kwargs)
    
    if request.method == 'GET':
        if 'animal_lookup_id-submitted' in request.GET:
            if forms['animal_lookup_id'].is_valid():
                animal = forms['animal_lookup_id'].cleaned_data['local_id']
                return redirect(animal)
        if 'animal_lookup_nmfs-submitted' in request.GET:
            if forms['animal_lookup_nmfs'].is_valid():
                animal = forms['animal_lookup_nmfs'].cleaned_data['nmfs_id']
                return redirect(animal)
        if 'animal_lookup_field_number-submitted' in request.GET:
            if forms['animal_lookup_field_number'].is_valid():
                animal = forms['animal_lookup_field_number'].cleaned_data['field_number']
                return redirect(animal)
        if 'case_lookup_id-submitted' in request.GET:
            if forms['case_lookup_id'].is_valid():
                case = forms['case_lookup_id'].cleaned_data['local_id']
                return redirect(case)
        if 'case_lookup_yearlynumber-submitted' in request.GET:
            form = forms['case_lookup_yearlynumber']
            if form.is_valid():
                year = form.cleaned_data['year']
                num = form.cleaned_data['number']
                case = YearCaseNumber.objects.get(year=year, number=num).case
                return redirect(case)
        if 'entanglement_lookup_nmfs-submitted' in request.GET:
            if forms['entanglement_lookup_nmfs'].is_valid():
                case = forms['entanglement_lookup_nmfs'].cleaned_data['nmfs_id']
                return redirect(case)
    
    template_media = Media()
    
    return render_to_response(
        'home.html',
        {
            # pass in some big querysets for database stats
            'animals': Animal.objects.all(),
            'cases': Case.objects.all(),
            'observations': Observation.objects.all(),
            'forms': forms,
            'media': reduce(lambda m, f: m + f.media, forms.values(), template_media),
        },
        RequestContext(request),
    )

def html_diff(old, new):
    '''\
    Generate a html representation of the difference between two  
    things. _Any_ two things.
    '''
    
    if new == old:
        return '<i>same</i>'
    
    if old is None:
        return "<span class=\"added\"><i>defined</i><span>"
    
    if new is None:
        return "<span class=\"removed\"><i>undefined</i></span>"
    
    if isinstance(old, numbers.Real) and isinstance(new, numbers.Real):
        diff = new - old
        if diff > 0:
            diff = u"+" + unicode(diff)
        elif diff < 0:
            diff = unicode(diff)
        else:
            diff = "<i>equivalent</i>"
        return diff
    
    #TODO really, this could work with any sequence of hashable objects 
    # with string representations...
    str_types = (str, unicode)
    seq_types = (list, tuple)
    if isinstance(old, str_types + seq_types) and isinstance(new, str_types + seq_types):
        # it looks better to just diff the string representations of 
        # lists and tuples
        if isinstance(old, seq_types):
            old = repr(old)
        if isinstance(new, seq_types):
            new = repr(new)
        sm = SequenceMatcher(None, old, new)
        diffstring = u''
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                diffstring += old[i1:i2]
            elif tag == 'delete':
                diffstring += u"<del>%s</del>" % old[i1:i2]
            elif tag == 'insert':
                diffstring += u"<ins>%s</ins>" % new[j1:j2]
            elif tag == 'replace':
                diffstring += u"<del>%s</del>" % old[i1:i2]
                diffstring += u"<ins>%s</ins>" % new[j1:j2]
            else:
                diffstring += '!!! unknown tag: %s' % tag
        return u"%s" % diffstring

    if isinstance(old, set) and isinstance(new, set):
        removed = old - new
        added = new - old

        diffstring = u''
        if removed:
            diffstring += u"<del>%s</del>" % unicode(removed)
        if added:
            diffstring += u"<ins>%s</ins>" % unicode(added)
        
        return diffstring
    
    if old.__class__ == new.__class__:
        return "<span class=\"changed\"><i>different %s</i></span>" % unicode(old.__class__.__name__)
    else:
        return "<i>%s -> %s</i>" % map(unicode, (old.__class__, new.__class__))

@login_required
def revision_detail(request, rev_id):
    
    rev = Revision.objects.get(id=rev_id)
    
    # annotate the versions with a reference to their previous versions
    annotated_versions = rev.version_set.all()
    
    for ver in annotated_versions:
        ver.old_version = None
        old_versions = Version.objects.filter(
            content_type= ver.content_type,
            object_id= ver.object_id,
            revision__date_created__lt= ver.revision.date_created,
        ).order_by('-revision__date_created')
        if old_versions.count():
            ver.old_version = old_versions[0]
        ver.new_version = None
        new_versions = Version.objects.filter(
            content_type= ver.content_type,
            object_id= ver.object_id,
            revision__date_created__gt= ver.revision.date_created,
        ).order_by('revision__date_created')
        if new_versions.count():
            ver.new_version = new_versions[0]
        else:
            # this is either the current version or was deleted
            # if it's current we don't need to worry about intervening schemata
            # changes and can safely vivify it to get the URL of it's page
            instance = ver.object_version.object
            if hasattr(instance, 'get_absolute_url'):
                try:
                    ver.url = instance.get_absolute_url()
                except NoReverseMatch:
                    pass

        fields = {}
        for name, value in ver.get_field_dict().items():
            fields[name] = {'new': value, 'old': None}

        if ver.old_version:
            for name, value in ver.old_version.get_field_dict().items():
                if not name in fields.keys():
                    fields[name] = {'new': None, 'old': None}
                fields[name]['old'] = value
        
        # compute diffs
        ver.differs = False
        for f in fields.values():
            if f['new'] != f['old']:
                ver.differs = True
                f['differ'] = True
            f['diff'] = mark_safe(html_diff(f['old'], f['new']))
        
        ver.fields = fields
    
    return render_to_response('reversion/revision_detail.html', {
        'rev': rev,
        'annotated_versions': annotated_versions,
        'media': Media(js=(settings.JQUERY_FILE, 'checkboxhider.js')),
    }, RequestContext(request))
    
@login_required
def object_history(request, content_type_id, object_id=None):
    content_type = ContentType.objects.get(id=content_type_id)
    
    versions = Version.objects.filter(content_type=content_type).order_by('revision__date_created')
    if not object_id is None:
        versions = versions.filter(object_id=object_id)
    
    meta_keys = set()
    field_keys = set()
    
    flat_versions = []
    
    for v in versions:
        if not v.format == 'json':
            print "!!! non-JSON version %d !!!" % v.id
            continue
        
        data = json.loads(v.serialized_data)
        if len(data) != 1:
            print "!!! weird list in version %d !!!" % v.id
            continue
        data = data[0]
        
        meta_keys.update(data.keys())
        
        fields = data['fields']
        field_keys.update(fields.keys())

    meta_keys.remove('fields')

    for v in versions:
        if not v.format == 'json':
            print "!!! non-JSON version %d !!!" % v.id
            continue
        
        data = json.loads(v.serialized_data)
        if len(data) != 1:
            print "!!! weird list in version %d !!!" % v.id
            continue
        data = data[0]

        flat_version = []

        for k in meta_keys:
            flat_version.append(data[k])
        flat_version.append(v.revision.user)
        flat_version.append(v.revision.date_created)

        fields = data['fields']
        for k in field_keys:
            flat_version.append(fields[k])
        flat_versions.append(flat_version)
    
    meta_keys.add('user')
    meta_keys.add('datetime')
        
    return render_to_response(
        'reversion/object_history.html', 
        {
            'object_id': object_id,
            'content_type': content_type,
            'meta_keys': map(lambda k: k.replace('_', ' '), meta_keys),
            'field_keys': map(lambda k: k.replace('_', ' '), field_keys),
            'flat_versions': flat_versions,
            'versions': versions,
        },
        RequestContext(request),
    )

@login_required
def new_case(request, initial_animal_id=None):
    '''\
    Presents a page to choose either an existing animal or the option to create
    a new one, and the type to case to create for that animal. No actual changes
    are made to the database (i.e. no cases or animals are created). Instead,
    when the form from this page is submitted, the response is a redirect to
    the correct add_<case_type>observation view, with the apropriate animal_id
    and case_id args filled in.
    '''
    
    form_classes = {
        'animal_choice': AnimalChoiceForm,
        'case_type': CaseTypeForm_factory(request.user),
    }

    form_kwargs = {}
    for name in form_classes.keys():
        form_kwargs[name] = {
            'prefix': name,
        }
        if request.GET:
            form_kwargs[name]['data'] = request.GET
    form_kwargs['animal_choice']['user'] = request.user
    if not initial_animal_id is None:
        form_kwargs['animal_choice']['initial'] = {
            'new_animal': '',
            'existing_animal': initial_animal_id,
        }

    forms = {}
    for name, f_class in form_classes.items():
        forms[name] = f_class(**form_kwargs[name])
    
    if reduce(lambda so_far, f: so_far and f.is_valid(), forms.values(), True):
        if forms['animal_choice'].can_add and forms['animal_choice'].cleaned_data['new_animal']:
            animal_id = None
        else:
            animal_id = forms['animal_choice'].cleaned_data['existing_animal'].id
        
        case_type = forms['case_type'].cleaned_data['case_type']
        
        # TODO don't hard-code case-types
        if case_type == 'Entanglement':
            return add_entanglementobservation(
                request,
                animal_id= animal_id,
            )

        if case_type == 'Shipstrike':
            return add_shipstrikeobservation(
                request,
                animal_id= animal_id,
            )
        
        return add_observation(request, animal_id=animal_id)
        
    template_media = Media()
    
    return render_to_response(
        'incidents/new_case.html',
        {
            'forms': forms,
            'media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

@permission_required('taxons.add_taxon')
def import_taxon(request):
    
    return unsecured_import_taxon(request)

@login_required
def odd_entries(request):
    
    contact_names = set(Contact.objects.exclude(Q(name='') | Q(name__isnull=True)).values_list('name', flat=True))
    contact_names |= set(Organization.objects.exclude(Q(name='') | Q(name__isnull=True)).values_list('name', flat=True))
    contacts_same_name = {}
    for name in contact_names:
        contacts = Contact.objects.filter(name=name)
        orgs = Organization.objects.filter(name=name)
        if contacts.count() + orgs.count() > 1:
            contacts_same_name[name] = list(contacts.all()) + list(orgs.all())
    
    field_numbers = set(Animal.objects.exclude(Q(field_number='') | Q(field_number__isnull=True)).values_list('field_number', flat=True))
    animals_same_number = {}
    for num in field_numbers:
        animals = Animal.objects.filter(field_number=num)
        if animals.count() > 1:
            animals_same_number[num] = animals
    
    animal_names = set()
    for a in Animal.objects.exclude(Q(name='') | Q(name__isnull=True)):
        for name in a.names:
            name = name.lower().strip()
            if not name == '':
                animal_names.add(name)
    animals_same_name = {}
    for name in animal_names:
        animals = Animal.objects.filter(name__icontains=name)
        if animals.count() > 1:
            animals_same_name[name] = animals
        
    no_cases = Animal.objects.filter(case__id__isnull=True)
    
    entanglement_numbers = set(Entanglement.objects.exclude(Q(nmfs_id='') | Q(nmfs_id__isnull=True)).values_list('nmfs_id', flat=True))
    entanglements_same_nmfs = {}
    for num in entanglement_numbers:
        ents = Entanglement.objects.filter(nmfs_id=num)
        if ents.count() > 1:
            entanglements_same_nmfs[num] = ents
    
    no_obs = Case.objects.filter(observation__id__isnull=True)
    
    ent_ids = Entanglement.objects.values_list('pk', flat=True)
    ss_ids = Shipstrike.objects.values_list('pk', flat=True)
    no_ent_obs_ext = Observation.objects.filter(cases__pk__in=ent_ids).filter(entanglements_entanglementobservation__isnull=True)
    no_ss_obs_ext = Observation.objects.filter(cases__pk__in=ss_ids).filter(shipstrikes_shipstrikeobservation__isnull=True)

    return render_to_response(
        'odd_entries.html',
        {
            'contacts_same_name': contacts_same_name,
            'animals_same_number': animals_same_number,
            'animals_same_name': animals_same_name,
            'animals_no_cases': no_cases,
            'cases_no_observations': no_obs,
            'entanglements_same_nmfs': entanglements_same_nmfs,
            'observations_no_ent': no_ent_obs_ext,
            'observations_no_ss': no_ss_obs_ext,
        },
        context_instance= RequestContext(request),
    )

