from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext

from cetacean_incidents.apps.animals.models import Animal

from models import Case, Entanglement
from forms import CreateCaseForm, EntanglementForm, visit_forms

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
    return {
        'Entanglement': edit_entanglement,
    }[case.detailed_class_name](request, case_id)

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
    
    # organize the form's fields into categories
    observer_fieldnames = (
        'date',
        'date_reported',
        'filer',
        'firsthand',
        'haz_loc_animal',
        'haz_loc_public',
        'letterholder',
        'location',
        'observer',
        'observer_comments',
        'time',
        'time_reported',
        'vessel',
    )
    animal_fieldnames = (
        'abandoned',
        'age_group',
        'age_method',
        'animal',
        'animal_description',
        'animal_heading',
        'animal_movement',
        'associates',
        'behaviour_description',
        'breathing',
        'can_breath',
        'condition',
        'dive_duration',
        'first_impression',
        'first_observed',
        'fluking',
        'gender',
        'gender_method',
        'head_out',
        'illness',
        'inaccessible',
        'injury',
        'intital_disposition_comment',
        'length',
        'length_method',
        'offspring',
        'other_findings',
        'other_initial_disposition',
        'out_of_habitat',
        'parents',
        'reported_name',
        'shot',
        'skin_condition',
        'taxon',
        'weight',
        'weight_health',
        'weight_method',
        'wound_age',
        'wounds',
    )
    visit_fieldnames = (
    )
    response_fieldnames = (
        'deemed_healthy',
        'died_at_site',
        'died_in_transport',
        'disentangled',
        'euthanized_at_site',
        'euthanized_in_transport',
        'findings_determined',
        'immediate_release',
        'left_at_site',
        'other_determination',
        'relocated',
        'transferred',
    )
    doc_fieldnames = (
        'media_loc',
        'media_taken',
        'media_taker',
        'photos_taken',
        'video_taken',
    )
    other_fieldnames = tuple(
        set(form.fields) 
        - set(observer_fieldnames)
        - set(animal_fieldnames)
        - set(visit_fieldnames)
        - set(response_fieldnames)
        - set(doc_fieldnames)
    )
    
    return render_to_response(
        'incidents/add_visit.html',
        {
            'form': form,
            'case': case,
            'observer_fields': map(
                lambda f: form[f],
                observer_fieldnames
            ),
            'animal_fields': map(
                lambda f: form[f],
                animal_fieldnames
            ),
            'visit_fields': map(
                lambda f: form[f],
                visit_fieldnames
            ),
            'response_fields': map(
                lambda f: form[f],
                response_fieldnames
            ),
            'doc_fields': map(
                lambda f: form[f],
                doc_fieldnames
            ),
            'other_fields': map(
                lambda f: form[f],
                other_fieldnames
            ),
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

