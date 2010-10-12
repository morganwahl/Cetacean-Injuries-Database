import re

try:
    import json
except ImportError:
    import simplejson as json # for python 2.5 compat.

import urllib
import urllib2

from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from models import Taxon
from django.shortcuts import render_to_response
from django.forms import Media
from django.template import RequestContext

from models import Taxon
 
def taxon_search(request):
    '''\
    Given a request with a query in the 'q' key of the GET string, returns a 
    JSON list of Taxons.
    '''
    
    get_query = u''
    if 'q' in request.GET:
        get_query = request.GET['q']
    
    words = get_query.split()
    if words:
        common_query = Q(common_names__icontains=get_query)
        
        genus_query = Q()
        abbr_match = re.search(r'^(?u)\s*(\w+)\.', words[0])
        if abbr_match:
            # the first word is a genus abbr, so remove it from the list of 
            # words
            words = words[1:]
            if len(words) == 0:
                # put in a dummy first word since latin_query assumes there will
                # be one
                words = ['']
            
            genuses = Taxon.objects.filter(rank=0, name__istartswith=abbr_match.group(1)).values_list('id', flat=True)
            if genuses:
                # add all their descendants to the results
                # TODO fetch more than 2 deep)
                genus_query |= Q(supertaxon__id__in=genuses)
                genus_query |= Q(supertaxon__supertaxon__id__in=genuses)
        
        latin_query = Q(name__istartswith=words[0])
        
        db_query = (common_query | latin_query) & genus_query
        results = Taxon.objects.filter(db_query).order_by('-rank', 'name')
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

def itis_search(request):
    get_string = urllib.urlencode(request.GET)
    url = 'http://www.itis.gov/ITISWebService/services/ITISService/searchForAnyMatch?' + get_string
    print "trying %s" % url
    return HttpResponse(urllib2.urlopen(url).read())

def taxon_import(request):

    template_media = Media(js= ('jquery/jquery-1.3.2.min.js',))

    return render_to_response(
        'taxons/import.html',
        {'media': template_media},
        context_instance=RequestContext(request),
    )
