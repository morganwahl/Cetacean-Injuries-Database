from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.db import models
from django.contrib.auth.decorators import login_required
from django.forms import Media

from reversion.models import Revision

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
                case = Case.objects.get(id=forms['case_lookup_id'].cleaned_data['local_id'])
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

    revisions = Revision.objects.all().order_by('-date_created')[:20]
    # annotate the revisions with the animals, cases, and observations they
    # concern
    for rev in revisions:
        rev.animals = set()
        rev.cases = set()
        rev.observations = set()
        rev.contacts = set()
        for v in rev.version_set.all():
            ct = v.content_type
            inst = v.get_object_version()
            # map inst to a Contact, Animal, Case, and/or Observation
            #if ct == ContentType.:
            #    rev.observations.add(inst)
            #    rev.cases.add(inst.case)
             #   rev.animals.add(inst.case.animal)
            if 'relevant_observation' in inst.__dict__:
                o = inst.relevant_observation
                rev.observations.add(o)
                rev.cases.add(o.case)
                rev.animals.add(o.case.animal)
            if 'relevant_case' in inst.__dict__:
                c = inst.relevant_case
                rev.cases.add(c)
                rev.animals.add(c.animal)
            if 'relevant_animal' in inst.__dict__:
                a = inst.relevant_animal
                rev.animals.add(a)
            if 'relevant_contact' in inst.__dict__:
                c = inst.relevant_contact
                rev.contacts.add(c)
    
    template_media = Media()
    
    return render_to_response(
        'home.html',
        {
            #'revisions': revisions,
            'forms': forms,
            'media': reduce(lambda m, f: m + f.media, forms.values(), template_media),
        },
        RequestContext(request),
    )

