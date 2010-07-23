import re

try:
    import simplejson as json# for 2.5 compat.
except ImportError:
    import json

from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from models import Taxon
from django.shortcuts import render_to_response

def taxon_search(request):
    '''\
    Given a request with a query in the 'q' key of the GET string, returns a 
    JSON list of Taxons.
    '''
    
    query = u''
    if 'q' in request.GET:
        query = request.GET['q']
    
    words = query.split()
    if words:
        firstword = words[0]
        query = Q(name__istartswith=firstword)
        query |= Q(common_names__icontains=query)
        abbr_match = re.search(r'^(?u)\s*(\w+)\.', firstword)
        if abbr_match:
            genuses = Taxon.objects.filter(rank=0, name__istartswith=abbr_match.group(1)).values_list('id', flat=True)
            if genuses:
                # add all their descendants to the results
                # TODO fetch more than 2 deep)
                query |= Q(supertaxon__id__in=genuses)
                query |= Q(supertaxon__supertaxon__id__in=genuses)
        results = Taxon.objects.filter(query).order_by('-rank', 'name')
    else:
        results = tuple()
    
    # since we wont have access to the handy properties and functions of the
    # Taxon objects, we have to call them now and include their output
    # in the JSON
    taxons = []
    for result in results:
        taxons.append({
            'id': result.id,
            'name': result.name,
            'display_name': unicode(result),
            'common_names': result.common_names,
        })
    # TODO return 304 when not changed?
    
    return HttpResponse(json.dumps(taxons))

