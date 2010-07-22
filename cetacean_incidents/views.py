import numbers

from difflib import SequenceMatcher

from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.db import models
from django.contrib.auth.decorators import login_required
from django.forms import Media
from django.utils.safestring import mark_safe

from reversion.models import Revision, Version

from cetacean_incidents.apps.incidents.models import Case, YearCaseNumber, Observation
from cetacean_incidents.apps.incidents.forms import CaseIDLookupForm, CaseNMFSIDLookupForm, CaseYearlyNumberLookupForm, CaseSearchForm

@login_required
def home(request):
    form_classes = {
        'case_lookup_id': CaseIDLookupForm,
        'case_lookup_yearlynumber': CaseYearlyNumberLookupForm,
        'case_lookup_nmfs': CaseNMFSIDLookupForm,
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
        return "<i>defined</i>"
    
    if new is None:
        return "<i>undefined</i>"
    
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
        return "<i>different %s</i>" % unicode(old.__class__.__name__)
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
    }, RequestContext(request))
    
