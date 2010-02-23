from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext

from models import Case, Entanglement
from forms import CreateCaseForm, CaseForm, EntanglementForm, observation_forms

@login_required
def edit_entanglement(request, case_id):
    case = Case.objects.get(id=case_id).detailed
    if request.method == 'POST':
        form = EntanglementForm(request.POST, instance=case)
        if form.is_valid():
            form.save()
            return redirect(case)
    else:
		form = EntanglementForm(instance=case)
    return render_to_response('incidents/edit_entanglement.html', {
        'taxon': case.probable_taxon,
        'gender': case.probable_gender,
        'form': form,
        'case': case,
        'entanglement': case,
    })

@login_required
def edit_case(request, case_id):
    # dispatch based on case type
    case = Case.objects.get(id=case_id)
    try:
        return {
            'Entanglement': edit_entanglement,
        }[case.detailed_class_name](request, case_id)
    except KeyError:
        pass

    if request.method == 'POST':
        form = CaseForm(request.POST, instance=case)
        if form.is_valid():
            form.save()
            return redirect(case)
    else:
		form = CaseForm(instance=case)
    return render_to_response('incidents/edit_case.html', {
        'taxon': case.probable_taxon,
        'gender': case.probable_gender,
        'form': form,
        'case': case,
    })

@login_required
def add_observation(request, case_id):
    case = Case.objects.get(id=case_id).detailed
    form_class = observation_forms[case.detailed_class_name]
    if request.method == 'POST':
        new_observation = case.observation_model(case=case)
        form = form_class(request.POST, instance=new_observation)
        if form.is_valid():
            form.save()
            return redirect('edit_case', case.id)
    else:
        form = form_class()
    
    return render_to_response(
        'incidents/add_observation.html',
        {
            'form': form,
            'case': case,
        },
        context_instance= RequestContext(request),
    )

@login_required
def create_case(request):
    if request.method == 'POST':
        form = CreateCaseForm(request.POST)
        if form.is_valid():
            # this is a little tricky: we'd like to make use of the form's
            # ability to create a new case from it's fields, but we also need 
            # that case to have a specific type, i.e. an Entanglement
            new_case = form.save()
            case_model = CreateCaseForm.type_models[form.cleaned_data['case_type']]
            case_extension = case_model.objects.create(case_ptr= new_case)
            return redirect('edit_case', case_extension.id)
    else:
        form = CreateCaseForm()
    return render_to_response(
        'incidents/create_case.html',
        {'form': form},
        context_instance= RequestContext(request),
    )

def merge_case(request, case1_id, case2_id):
    # synthesize the values from the two cases to create the ones for the merged
    # case. we'll actually be modifiying the 'older' of the two, not creating a
    # new one. 'older' means coming earlier when sorting by case.date.year, 
    # case.yearly_number, ascending. if a case has no date (should only occur
    # if it has no observations yet), it's the "newer" one. if neither case has
    # a date, order them by their database IDs.
    
    # TODO check that the cases (and case.observation_models?) are the same type
    case1 = Case.objects.get(id=case1_id)
    case2 = Case.objects.get(id=case2_id)
    
    # we make case1 the older_case by default, so we only need to check for
    # conditions where case2 is older; if any are found, we switch them
    (older_case, newer_case) = (case1, case2)
    switch = False
    
    # check for null dates
    if older_case.date is None:
        if newer_case.date is not None:
            switch = True
        else:
            # sort by IDs
            if newer_case.id < older_case.id:
                switch = True
    elif newer_case.date is not None:
        if newer_case.date.year < older_case.date.year:
            switch = True
        elif newer_case.date.year == older_case.date.year:
            if newer_case.yearly_number < older_case.yearly_number:
                switch = True
            elif newer_case.yearly_number == older_case.yearly_number:
                # TODO should never get here!
                pass
    
    if newer_case.date is not None:
        if older_case.date is None:
            switch = True
        elif newer_case.date.year < older_case.date.year:
            switch = True
        elif newer_case.date.year == older_case.date.year:
            if newer_case.yearly_number < older_case.yearly_number:
                switch = True
    elif older_case.date is None:
        # sort by IDs
        if newer_case.id < older_case.id:
            switch = True
    
    if switch:
        (older_case, newer_case) = (newer_case, older_case)
    
    if request.method == 'POST':
        form = MergeCaseForm(request.POST, older_case)
        if form.is_valid():
            form.save()
            # make sure we get all the past names
            older_case.names_set = older_case.names_set | newer_case.names_set
            # move all the observations. 
            # TODO not sure if save() func gets called when you do QuerySet.update()...
            for o in newer_case.observation_set.all():
                o.case = older_case
                o.save()
            # delete newer_case
            newer_case.delete()
            return redirect('case_detail', older_case.id)
    else:
        # compare the fields in the two cases, one by one
        
        # animal should be the one from the older_case
        animal = older_case.animal.id
        
        # merge the ole_investigation NullableBoolean
        # abbr. for convience.
        ole_investigation = None
        if not older_case.ole_investigation is None:
            # the older case isn't unknown
            if not newer_case.ole_investigation is None:
                # the newer case isn't unknown
                if older_case.ole_investigation == newer_case.ole_investigation:
                    # two cases are the same
                    ole_investigation = older_case.ole_investigation
            else:
                # the newer case is unknown
                ole_investigation = older_case.ole_investigation
        else:
            # the older case is unknown
            if not newer_case.ole_investigation is None:
                # the newer case isn't
                ole_investigation = newer_case.ole_investigation
        
        form = MergeCaseForm(
            data= {
                'animal': animal,
                'ole_investigation': ole_investigation,
            },
            instance= older_case,
        )
            
    return render_to_response(
        'incidents/merge_case.html',
        {
            'form': form,
            'older_case': older_case,
            'newer_case': newer_case,
        },
    )

