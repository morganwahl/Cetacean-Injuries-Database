from base64 import standard_b64encode
import operator

try:
    import json
except ImportError:
    import simplejson as json # for python 2.5 compat.

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.forms import Media
from django.http import HttpResponse
from django.shortcuts import (
    render_to_response,
    redirect,
)
from django.template import RequestContext

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.generic_templates.templatetags.html_filter import html

from cetacean_incidents.apps.taxons.models import Taxon

from ..forms import (
    AnimalForm,
    AnimalMergeSourceForm,
    AnimalMergeForm,
    AnimalSearchForm,
)
from ..models import Animal

@login_required
def animal_detail(request, animal_id):
    
    animal = Animal.objects.get(id=animal_id)
        
    context = {
        'animal': animal,
        'media': Media(),
    }

    if request.user.has_perms(('incidents.change_animal', 'incidents.delete_animal')):
        merge_form = AnimalMergeSourceForm(destination=animal)
        context['merge_form'] = merge_form
        context['media'] += merge_form.media
        context['media'] += Media(js=(settings.JQUERY_FILE,))
    
    return render_to_response(
        'incidents/animal_detail.html',
        context,
        context_instance= RequestContext(request),
    )

@login_required
def animal_search(request):
    # prefix should be the same as the on used on the homepage
    prefix = 'animal_search'
    form_kwargs = {
        'prefix': 'animal_search',
    }
    if request.GET:
        form_kwargs['data'] = request.GET
    form = AnimalSearchForm(**form_kwargs)
    
    animal_list = tuple()
    
    if form.is_valid():
        #animal_order_args = ('id',)
        #animals = Animal.objects.all().distinct().order_by(*animal_order_args)
        # TODO Oracle doesn't support distinct() on models with TextFields
        #animals = Animal.objects.all().order_by(*animal_order_args)
        
        #if form.cleaned_data['taxon']:
        #    t = form.cleaned_data['taxon']
        #    descendants = Taxon.objects.with_descendants(t)
        #    animals = animals.filter(Q(determined_taxon__in=descendants) | Q(case__observation__taxon__in=descendants))
        
        # empty string for name is same as None
        #if form.cleaned_data['name']:
        #    name = form.cleaned_data['name']
        #    name_q = Q(name__icontains=name)
        #    field_number_q = Q(field_number__icontains=name)
        #    animals = animals.filter(name_q | field_number_q)

        # simulate distinct() for Oracle
        # an OrderedSet in the collections library would be nice...
        # TODO not even a good workaround, since we have to pass in the count
        # seprately
        #seen = set()
        #animal_list = list()
        #for a in animals:
        #    if not a in seen:
        #        seen.add(a)
        #        animal_list.append(a)
        
        animal_list = form.results()

    return render_to_response(
        "incidents/animal_search.html",
        {
            'form': form,
            'media': form.media,
            'animal_list': animal_list,
            'animal_count': len(animal_list),
        },
        context_instance= RequestContext(request),
    )

# TODO how to secure this view?
def animal_search_json(request):
    '''\
    Given a request with a query in the 'q' key of the GET string, returns a 
    JSON list of Animals.
    '''
    
    query = u''
    if 'q' in request.GET:
        query = request.GET['q']
    
    # we only do case-less matching that ignore whitespace, so use a case-less, stripped key
    cache_key = query.lower().strip()
    # some cache backends are picky about characters, so use Base64-encoded
    # UTF-8
    cache_key = cache_key.encode('utf-8')
    cache_key = standard_b64encode(cache_key)
    cache_key = 'animal_search_json_' + cache_key
    cached_json = cache.get(cache_key)
    if cached_json:
        return HttpResponse(cached_json)
    
    words = query.split()
    if words:
        firstword = words[0]
        q = Q(name__icontains=firstword)
        q |= Q(field_number__icontains=firstword)
        try:
            q |= Q(id__exact=int(firstword))
        except ValueError:
            pass
        results = Animal.objects.filter(q).order_by('-id')
    else:
        results = tuple()
    
    # since we wont have access to the handy properties and functions of the
    # Animal objects, we have to call them now and include their output
    # in the JSON
    animals = []
    for result in results:
        
        plain_name = unicode(result)
        
        html_name = html(result, block=True)

        taxon = result.determined_taxon
        if taxon:
            taxon = unicode(taxon.scientific_name())
        
        animals.append({
            'id': result.id,
            'plain_name': plain_name,
            'html_name': html_name,
            'taxon': taxon,
        })
    # TODO return 304 when not changed?
    
    json_result = json.dumps(animals)
    cache.set(cache_key, json_result, 60) # timeout quickly to catch updates
                                          # to the animals
    return HttpResponse(json_result)

@login_required
@permission_required('incidents.add_animal')
def create_animal(request):
    if request.method == 'POST':
        form = AnimalForm(request.POST)
        if form.is_valid():
            new_animal = form.save()
            return redirect(new_animal)
    else:
        form = AnimalForm()

    template_media = Media()

    return render_to_response(
        'incidents/create_animal.html',
        {
            'form': form,
            'media': template_media + form.media
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('incidents.change_animal')
def edit_animal(request, animal_id):
    animal = Animal.objects.get(id=animal_id)
    form_kwargs = {
        'instance': animal,
    }
    if animal.determined_dead_before or animal.necropsy:
        form_kwargs['initial'] = {
            'dead': True,
        }
    
    if request.method == 'POST':
        form = AnimalForm(request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect('animal_detail', animal.id)
    else:
        form = AnimalForm(**form_kwargs)

    template_media = Media(js=(settings.JQUERY_FILE, 'checkboxhider.js'))

    return render_to_response(
        'incidents/edit_animal.html',
        {
            'animal': animal,
            'form': form,
            'media': template_media + form.media
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('incidents.change_animal')
@permission_required('incidents.delete_animal')
def animal_merge(request, destination_id, source_id=None):
    # the "source" animal will be deleted and references to it will be change to
    # the "destination" animal
    
    destination = Animal.objects.get(id=destination_id)
    
    if source_id is None:
        merge_form = AnimalMergeSourceForm(destination, request.GET)
        if not merge_form.is_valid():
            return redirect('animal_detail', destination.id)
        source = merge_form.cleaned_data['source']
    else:
        source = Animal.objects.get(id=source_id)

    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = AnimalMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            form.delete()
            return redirect('animal_detail', destination.id)
    else:
        form = AnimalMergeForm(**form_kwargs)
    
    return render_to_response(
        'incidents/animal_merge.html',
        {
            'object_name': 'animal entry',
            'object_name_plural': 'animal entries',
            'destination': destination,
            'source': source,
            'form': form,
            'media': form.media,
        },
        context_instance= RequestContext(request),
    )

