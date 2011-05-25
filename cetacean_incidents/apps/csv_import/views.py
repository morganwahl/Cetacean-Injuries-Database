from django.core.paginator import (
    EmptyPage,
    InvalidPage,
    Paginator,
)
from django.db import transaction
from django.db.models import Q
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import RequestContext

from django.contrib.auth.decorators import login_required

from reversion import revision

from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.documents.models import Documentable

from cetacean_incidents.apps.incidents.models import Animal

from . import IMPORT_TAGS

from forms import ImportCSVForm

import observations_parse
from observations_parse import ImportObservationsCSVForm

import strandings_parse

# TODO perms
@login_required
@transaction.commit_on_success
@revision.create_on_success
def import_stranding_csv(request):
    
    results = None
    if request.method == 'POST':
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            
            results = strandings_parse.parse_csv(form.cleaned_data['csv_file'])
    
            if not form.cleaned_data['test_run']:
                strandings_parse.process_results(results, form.cleaned_data['csv_file'].name, request.user)
                return redirect('home')
            
    else:
        form = ImportCSVForm()

    return render_to_response(
        'csv_import/import.html',
        {
            'import_type': 'strandings',
            'form': form,
            'media': form.media,
            'results': results,
        },
        context_instance= RequestContext(request),
    )

def import_observations_csv(request):
    
    results = None
    if request.method == 'POST':
        form = ImportObservationsCSVForm(request.POST, request.FILES)
        if form.is_valid():
            
            results = observations_parse.parse_csv(form.cleaned_data['csv_file'], form.cleaned_data['original_observation'])
    
            if not form.cleaned_data['test_run']:
                observations_parse.process_results(results, form.cleaned_data['csv_file'].name, request.user)
                return redirect('home')
            
    else:
        form = ImportObservationsCSVForm()

    return render_to_response(
        'csv_import/import.html',
        {
            'import_type': 'observations',
            'form': form,
            'media': form.media,
            'results': results,
        },
        context_instance= RequestContext(request),
    )
    
def review_imports(request):
    
    tagged = Documentable.objects.filter(tag__tag_text__in=IMPORT_TAGS).values_list('id', flat=True)
    
    animal_filter = Q(id__in=tagged)
    animal_filter |= Q(case__id__in=tagged)
    animal_filter |= Q(observation__id__in=tagged)
    
    # note that Oracle doesn't support DISTINCT
    animals = Animal.objects.filter(
        animal_filter
    ).order_by('observation__datetime_observed', 'case__id', 'id')
    
    animal_pages = Paginator(animals, 10)

    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        animals = animal_pages.page(page)
    except (EmptyPage, InvalidPage):
        animals = animal_pages.page(paginator.num_pages)

    return render_to_response(
        'csv_import/review.html',
        {
            'animals': animals,
            'tagged': tagged,
        },
        context_instance= RequestContext(request),
    )

