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
    
    # organize the form's fields into categories
    observer_fieldnames = (
        'date',
        'time',
        'location',
        'observer',
        'reporter',
        'vessel',
        'verified_sighting',
        'verified_method',
    )
    animal_fieldnames = (
        'animal',
        'taxon',
        'gender',
        'gender_method',
        'age',
        'age_group',
        'age_method',
        'length',
        'length_method',
        'size_description',
        'color',
        'head_description',
        'back_description',
        'tail_description',
        'flippers_description',
        'visible_injuries',
        'visible_blood',
        'scars_or_chafing',
        'appears_thin',
        'rough_skin',
    )
    visit_fieldnames = (
        'weather',
        'visibility',
        'visibility_distance',
        'wind_speed',
        'wind_direction',
        'wave_height',
        'swell_height',
        'water_depth',
        'seasurface_temp',
        'bottom_type',
    )
    visit_fieldnames += {
        'Entanglement': (
            'entanglement_status',
            'body_part_entangled',
            'level_of_constriction',
            'visible_lines',
            'trailing_gear',
            'buoys_present',
            'buoy_markings',
            # general gear fields
            'gear_collected',
            'gear_sent_to',
            'gear_analysis',
            # specific gear fields
            'gear_retrieved_date',
            'gear_received_date',
            'gear_retrieved_contact',
            'gear_received_from',
            'gear_type',
            'target_species',
            'gear_amount',
            'gear_owner',
            'gear_set_date',
            'gear_set_location',
            'gear_set_assymetry',
            'gear_missing_date',
            'gear_missing_amount',
            'gear_comments',
        )
    }[case.detailed_class_name]
    response_fieldnames = (
        'visual_health',
        'thermal_imaging',
        'respiration_analysis',
        'fecal_analysis',
        'skin_culture',
        'disentanglement_attempt',
    )
    doc_fieldnames = (
        'photos_location',
        'photos_contact',
        'videos_location',
        'videos_contact',
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

