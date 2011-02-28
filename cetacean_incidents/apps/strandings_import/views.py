from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from reversion import revision

from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.documents.models import Documentable
from cetacean_incidents.apps.incidents.models import Animal, Case, Observation

from forms import ImportCSVForm
from csv_import import parse_csv, process_results, IMPORT_TAGS
    
# TODO perms
@login_required
@transaction.commit_on_success
@revision.create_on_success
def import_csv(request):
    
    results = None
    if request.method == 'POST':
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            
            results = parse_csv(form.cleaned_data['csv_file'])
    
            if not form.cleaned_data['test_run']:
                process_results(results, form.cleaned_data['csv_file'].name, request.user)
                return redirect('home')
            
    else:
        form = ImportCSVForm()

    return render_to_response(
        'strandings_import/import.html',
        {
            'form': form,
            'media': form.media,
            'results': results,
        },
        context_instance= RequestContext(request),
    )
    
def review_imports(request):
    
    tagged = Documentable.objects.filter(tag__tag_text__in=IMPORT_TAGS).values_list('id', flat=True)
    
    tagged_animal = Q(id__in=tagged)
    tagged_case = Q(case__id__in=tagged)
    tagged_obs = Q(observation__id__in=tagged)
    
    # Oracle doesn't supprot DISTINCT
    animal_set = set()
    animal_list = []
    for a in Animal.objects.filter(
        tagged_animal | tagged_case | tagged_obs
    ).order_by('observation__datetime_observed', 'case__id', 'id'):
        if a not in animal_set:
            animal_set.add(a)
            animal_list.append(a)
    
    return render_to_response(
        'strandings_import/review.html',
        {
            'animals': animal_list,
            'tagged': tagged,
        },
        context_instance= RequestContext(request),
    )

