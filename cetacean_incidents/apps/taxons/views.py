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
        results = Taxon.objects.filter(Q(name__istartswith=firstword) | Q(common_names__icontains=query)).order_by('-rank', 'name')
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

from forms import TestForm
def testview(request):
    if request.method == 'POST': # If the form has been submitted...
        form = TestForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            # ...
            return HttpResponseRedirect('/') # Redirect after POST
    else:
        form = TestForm() # An unbound form

    return render_to_response('taxons/test.html', {
        'form': form,
    })

