from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext

from models import Case, Entanglement
from forms import CreateCaseForm, CaseForm, EntanglementForm, visit_forms

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
def add_visit(request, case_id):
    case = Case.objects.get(id=case_id).detailed
    form_class = visit_forms[case.detailed_class_name]
    if request.method == 'POST':
        new_visit = case.visit_model(case=case)
        form = form_class(request.POST, instance=new_visit)
        if form.is_valid():
            form.save()
            return redirect('edit_case', case.id)
    else:
        form = form_class()
    
    return render_to_response(
        'incidents/add_visit.html',
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

