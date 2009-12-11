import json
from django.db.models import Q
from django.http import HttpResponse
from models import Taxon

def taxon_search(request):
    '''\
    Given a request with a query in the 'q' key of the GET string, returns a 
    JSON list of Taxons.
    '''
    
    query = u''
    if 'q' in request.GET:
        query = request.GET['q']
    
    results = Taxon.objects.filter(Q(name__istartswith=query) | Q(common_name__icontains=query))
    
    # since we wont have access to the handy properties and functions of the
    # Taxon objects, we have to call them now and include their output
    # in the JSON
    taxons = []
    for result in results:
        taxons.append({
            'id': result.id,
            'name': result.name,
            'display_name': unicode(result),
            'common_name': result.common_name,
        })
    
    return HttpResponse(json.dumps(taxons))

