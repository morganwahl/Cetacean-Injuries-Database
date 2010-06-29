from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.db import models

from reversion.models import Revision

from cetacean_incidents.apps.incidents.models import Case, Observation
from cetacean_incidents.apps.incidents.forms import CaseLookupForm, CaseSearchForm

def home(request):
    if request.method == 'GET':
        if 'local_id' in request.GET:
            case_lookup_form = CaseLookupForm(request.GET)
            if case_lookup_form.is_valid():
                # TODO error-handling
                case = Case.objects.get(id=case_lookup_form.cleaned_data['local_id'])
                return redirect(case)
        else:
            case_lookup_form = CaseLookupForm()
            
        if request.GET:
            case_search_form = CaseSearchForm(request.GET)
        else:
            case_search_form = CaseSearchForm()

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
        
    return render_to_response(
        'home.html',
        {
            #'revisions': revisions,
            'case_lookup_form': case_lookup_form,
            'case_search_form': case_search_form,
        },
        RequestContext(request),
    )

