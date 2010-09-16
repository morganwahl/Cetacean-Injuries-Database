import numbers

from difflib import SequenceMatcher

from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.db import models
from django.contrib.auth.decorators import login_required
from django.forms import Media
from django.utils.safestring import mark_safe
from django.core.urlresolvers import NoReverseMatch
from django.conf import settings

from reversion.models import Revision, Version

from forms import AnimalChoiceForm, CaseTypeForm

from cetacean_incidents.apps.incidents.models import Case, YearCaseNumber, Observation
from cetacean_incidents.apps.incidents.forms import AnimalIDLookupForm, AnimalSearchForm, CaseIDLookupForm, CaseNMFSIDLookupForm, CaseYearlyNumberLookupForm, CaseSearchForm
from cetacean_incidents.apps.incidents.views import add_observation
from cetacean_incidents.apps.entanglements.views import add_entanglementobservation
from cetacean_incidents.apps.shipstrikes.views import add_shipstrikeobservation

@login_required
def home(request):
    form_classes = {
        'animal_lookup_id': AnimalIDLookupForm,
        'case_lookup_id': CaseIDLookupForm,
        'case_lookup_yearlynumber': CaseYearlyNumberLookupForm,
        'case_lookup_nmfs': CaseNMFSIDLookupForm,
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
        if 'case_lookup_nmfs-submitted' in request.GET:
            if forms['case_lookup_nmfs'].is_valid():
                case = forms['case_lookup_nmfs'].cleaned_data['nmfs_id']
                return redirect(case)
    
    template_media = Media()
    
    return render_to_response(
        'home.html',
        {
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
def new_case(request):
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
        'case_type': CaseTypeForm,
    }

    form_kwargs = {}
    for name in form_classes.keys():
        form_kwargs[name] = {
            'prefix': name,
        }
        if request.GET:
            form_kwargs[name]['data'] = request.GET

    forms = {}
    for name, f_class in form_classes.items():
        forms[name] = f_class(**form_kwargs[name])
    
    if reduce(lambda so_far, f: so_far and f.is_valid(), forms.values(), True):
        animal = forms['animal_choice'].cleaned_data['animal']
        animal_id = None
        if not animal is None:
            animal_id = animal.id
        
        case_type = forms['case_type'].cleaned_data['case_type']
        
        # TODO don't hard-code case-types
        if case_type == 'Entanglement':
            return add_entanglementobservation(
                request,
                animal_id= animal_id,
                entanglement_id= None,
            )

        if case_type == 'Shipstrike':
            return add_shipstrikeobservation(
                request,
                animal_id= animal_id,
                shipstrike_id= None,
            )
        
        return add_observation(
            request,
            animal_id= animal_id,
            case_id= None,
        )
        
    template_media = Media()
    
    return render_to_response(
        'incidents/new_case.html',
        {
            'forms': forms,
            'media': reduce( lambda m, f: m + f.media, forms.values(), template_media),
        },
        context_instance= RequestContext(request),
    )

