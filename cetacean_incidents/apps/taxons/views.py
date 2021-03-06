from base64 import standard_b64encode
import re
from StringIO import StringIO

try:
    import json
except ImportError:
    import simplejson as json # for python 2.5 compat.

import urllib
import urllib2

from lxml import etree
from lxml import objectify

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.forms import Media
from django.http import HttpResponse
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import RequestContext
from django.template.loader import render_to_string

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required
from cetacean_incidents.forms import merge_source_form_factory

from cetacean_incidents.apps.generic_templates.templatetags.html_filter import html

from forms import TaxonMergeForm
from models import Taxon

@login_required
def taxon_tree(request, root_id=None):
    
    if root_id is None:
        root_taxa = Taxon.objects.filter(supertaxon__isnull=True)
        taxa_name = 'root taxa'
    else:
        root_taxa = Taxon.objects.filter(supertaxon=root_id)
        taxa_name = 'subtaxa of %s' % unicode(Taxon.objects.get(id=root_id))
    
    return render_to_response(
        'taxons/taxon_tree.html',
        {
            'taxa_name': taxa_name,
            'taxa': root_taxa,
        },
        context_instance= RequestContext(request),
    )

def taxon_search_json(request):
    '''\
    Given a request with a query in the 'q' key of the GET string, returns a 
    JSON list of Taxons.
    '''
    
    get_query = u''
    if 'q' in request.GET:
        get_query = request.GET['q']
    
    cache_key = get_query.lower().strip()
    # some cache backends are picky about characters, so use Base64-encoded
    # UTF-8
    cache_key = cache_key.encode('utf-8')
    cache_key = standard_b64encode(cache_key)
    cache_key = 'taxon_search_json_%s' % cache_key
    cached_json = cache.get(cache_key)
    if cached_json:
        return HttpResponse(cached_json)
    
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
    taxa = []
    for result in results:
        taxa.append({
            'id': result.id,
            'plain_name': result.scientific_name(),
            'html_name': html(result),
            'common_names': result.common_names,
        })
    # TODO return 304 when not changed?
    
    json_result = json.dumps(taxa)
    # we can do a long timeout since adding or editing a new Taxon will clear
    # the cache
    cache.set(cache_key, json_result, 7 * 24 * 60 * 60)
    return HttpResponse(json_result)

# remove stale cache entries
def _taxon_post_save(sender, **kwargs):
    # sender should be Taxon
    
    # no way to know what taxon_search_json keys would match the changed Taxon,
    # so we just have to clear the cache
    cache.clear()

models.signals.post_save.connect(
    sender= Taxon,
    receiver= _taxon_post_save,
    dispatch_uid= 'cache_clear__taxon_search_json__taxon__post_save',
)

@login_required
def taxon_detail(request, taxon_id):
    
    taxon = Taxon.objects.get(id=taxon_id)
    
    merge_form = merge_source_form_factory(Taxon, taxon)()
    template_media = Media(
        js= (settings.JQUERY_FILE,),
    )
    
    return render_to_response(
        'taxons/taxon_detail.html',
        {
            'taxon': taxon,
            'media': template_media + merge_form.media,
            'merge_form': merge_form,
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('taxons.change_taxon')
@permission_required('taxons.delete_taxon')
def taxon_merge(request, destination_id, source_id=None):
    # the "source" taxon will be deleted and references to it will be changed
    # to the "destination" taxon
    
    destination = Taxon.objects.get(id=destination_id)

    if source_id is None:
        merge_form = merge_source_form_factory(Taxon, destination)(request.GET)

        if not merge_form.is_valid():
            return redirect('taxon_detail', destination.id)
        source = merge_form.cleaned_data['source']
    else:
        source = Taxon.objects.get(id=source_id)
    
    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = TaxonMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect('taxon_detail', destination.id)
    else:
        form = TaxonMergeForm(**form_kwargs)
    
    return render_to_response(
        'taxons/merge_taxon.html',
        {
            'destination': destination,
            'source': source,
            'form': form,
            'media': form.media,
            'destination_fk_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.destination_fk_refs
            ),
            'source_fk_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.source_fk_refs
            ),
            'destination_m2m_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.destination_m2m_refs
            ),
            'source_m2m_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.source_m2m_refs
            ),
        },
        context_instance= RequestContext(request),
    )

class ITIS_Error(Exception):
    pass

itis_namespaces = {
    'ns': "http://itis_service.itis.usgs.org",
    'ax': "http://data.itis_service.itis.usgs.org/xsd",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
}
    
def _get_itis(funcname, get_args={}):
    '''Given an ITIS WebServices function name and a dictionary of args, returns a parse xml document of the results. Raises an ITIS_Error Exception on errors.'''
    # TODO can't urllib compose a document and get-string for us?
    url = 'http://www.itis.gov/ITISWebService/services/ITISService/' + funcname + '?' + urllib.urlencode(get_args)
    xml = cache.get(url)
    if xml is None:
        url_handle = urllib2.urlopen(url)
        # ITIS doesn't send HTTP error codes when its database is down. :-(
        # check for a mimetype of text/html instead
        if url_handle.info().gettype() == 'text/html':
            raise ITIS_Error(render_to_string('taxons/itis_error_include.html', {'error_url': url}))
        xml = url_handle.read()
        cache.set(url, xml, 7 * 24 * 60 * 60) # timeout of one week
    
    # use parse instead of fromstring since it expects a full document, which
    # is what we have
    result = etree.parse(StringIO(xml))
    
    return result

def _is_animal(tsn):
    # http://www.itis.gov/ITISWebService/services/ITISService/getKingdomNameFromTSN?tsn=202385
    xml_doc = _get_itis('getKingdomNameFromTSN', {'tsn': tsn})
    
    kingdom_id_elements = xml_doc.xpath('//ns:return/ax:kingdomId', namespaces=itis_namespaces)
    kingdom_id = int(kingdom_id_elements[0].text)
    
    return kingdom_id == 5

def itis_get_rank(tsn):
    # if it's already been imported just look it up locally
    q = Taxon.objects.filter(tsn=tsn)
    if q.exists():
        for (itis_rank_name, rank) in Taxon.ITIS_RANKS.items():
            if rank == q[0].rank:
                return itis_rank_name

    # http://www.itis.gov/ITISWebService/services/ITISService/getTaxonomicRankNameFromTSN?tsn= 202385
    xml_doc = _get_itis('getTaxonomicRankNameFromTSN', {'tsn': tsn})
    
    itis_rankname = xml_doc.xpath("//ns:return/ax:rankName", namespaces=itis_namespaces)[0].text
    
    return itis_rankname
    
def itis_search(request):
    xml_doc = _get_itis('searchForAnyMatch', request.GET)
    
    match_elements = xml_doc.xpath("//ns:return/ax:anyMatchList", namespaces=itis_namespaces)
    
    results = []
    for e in match_elements:
        # TODO better way to transmute an etree element into a objectified 
        # element
        o = objectify.fromstring(etree.tostring(e))
        if not len(o): # no matches were returned
            break
        
        try:
            taxon = Taxon.objects.get(tsn=o.tsn)
        except:
            taxon = Taxon()
        
            taxon.tsn = o.tsn
            taxon.name = o.sciName
            taxon.itis_rank = itis_get_rank(o.tsn)
            taxon.rank = Taxon.ITIS_RANKS[taxon.itis_rank]

        # skip taxa above Order
        if taxon.rank > 2:
            continue
        
        common_names = []
        for name in o.commonNameList.commonNames:
            if len(name):
                if name.language == 'English':
                    common_names.append(unicode(name.commonName))
        taxon.common_names = ', '.join(common_names)
        
        results.append(taxon)
    
    # render an HTML fragment that can be inserted into the taxon_import page
    return HttpResponse(
        render_to_string('taxons/itis_search_results.html', {
            'results': results,
            'MEDIA_URL': settings.MEDIA_URL,
        }),
        mimetype="text/plain",
    )

def import_search(request):
    template_media = Media(js=(settings.JQUERY_FILE,))
    
    return render_to_response(
        'taxons/import_search.html',
        {'media': template_media},
        context_instance=RequestContext(request),
    )

def import_tsn(request, tsn):
    if request.method == 'POST':
        tsn_list = request.POST['taxa']
        
        tsns = map(int, tsn_list.split(','))
        
        for tsn in tsns:
            taxon = add_taxon(tsn)
            taxon.save()
    
    # http://www.itis.gov/ITISWebService/services/ITISService/getFullHierarchyFromTSN?tsn=1378
    xml_doc = _get_itis('getFullHierarchyFromTSN', {'tsn': tsn})
    
    taxa_elements = xml_doc.xpath("//ns:return/ax:hierarchyList", namespaces=itis_namespaces)
    
    taxa_info = {}
    taxa_children = {}
    to_add = set()
    root_taxon = None
    for e in taxa_elements:
        o = objectify.fromstring(etree.tostring(e))
        tsn = int(o.tsn)
        rank_name = unicode(o.rankName)
        rank = Taxon.ITIS_RANKS[rank_name]
        # skip taxa above Order
        if rank > 2:
            continue
        # the Order is our root taxon
        # TODO multiple orders?
        if rank == 2:
            root_taxon = tsn
        taxa_info[tsn] = {
            'tsn': tsn,
            'name': unicode(o.taxonName),
            'itis_rank': rank_name,
            'exists': Taxon.objects.filter(tsn=tsn).exists(),
        }
        if not tsn == root_taxon:
            parent = int(o.parentTsn)
            taxa_info[tsn]['supertaxon'] = parent
            if not parent in taxa_children.keys():
                taxa_children[parent] = []
            taxa_children[parent].append(tsn)
        
    # sort into the hierarchy
    def _info_for_tsn(tsn, level):
        info = taxa_info[tsn]
        if tsn in taxa_children.keys():
            children = taxa_children[tsn]
        else:
            children = []
        
        info['level'] = level
        
        results = [info]
        for child in children:
            child_info = _info_for_tsn(child, level + 2)
            results += child_info
        
        return results
    
    taxa_list = _info_for_tsn(root_taxon, 0)
    
    to_add = []
    for taxon in taxa_list:
        if not taxon['exists']:
            to_add.append(taxon['tsn'])
    
    return render_to_response(
        'taxons/import_tsn.html',
        {
            'tsn': tsn,
            'taxa': taxa_list,
            'to_add': to_add,
        },
        context_instance=RequestContext(request),
    )

def add_taxon(tsn):
    #http://www.itis.gov/ITISWebService/services/ITISService/getScientificNameFromTSN?tsn=531894
    
    taxon = Taxon(tsn=tsn)
    
    sci_name_xml = _get_itis('getScientificNameFromTSN', {'tsn': tsn})
    sci_name = None
    for i in range(1,5):
        this_name = sci_name_xml.xpath("//ns:return/ax:unitName%d" % i, namespaces=itis_namespaces)[0].text
        if this_name:
            sci_name = this_name
    taxon.name = sci_name
    
    rank_name_xml = _get_itis('getTaxonomicRankNameFromTSN', {'tsn': tsn})
    rank_name = rank_name_xml.xpath("//ns:return/ax:rankName", namespaces=itis_namespaces)[0].text
    taxon.rank = Taxon.ITIS_RANKS[rank_name]

    supertaxon_xml = _get_itis('getParentTSNFromTSN', {'tsn': tsn})
    supertaxon_tsn = supertaxon_xml.xpath("//ns:return/ax:parentTsn", namespaces=itis_namespaces)[0]
    supertaxon_tsn = int(supertaxon_tsn.text)
    q = Taxon.objects.filter(tsn=supertaxon_tsn)
    if q.exists():
        taxon.supertaxon = q[0]
    
    common_names_xml = _get_itis('getCommonNamesFromTSN', {'tsn': tsn})
    common_names_elements = common_names_xml.xpath("//ns:return/ax:commonNames", namespaces=itis_namespaces)
    common_names = []
    for name in common_names_elements:
        name = objectify.fromstring(etree.tostring(name))

        nil_key = '{%s}nil' % itis_namespaces['xsi']
        if nil_key in name.attrib:
            if name.attrib[nil_key] == 'true':
                continue

        if not len(name):
            continue

        if name.language != "English":
            continue

        common_names.append(unicode(name.commonName))
    taxon.common_names = ", ".join(common_names)
        
    return taxon

