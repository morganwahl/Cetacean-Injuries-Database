from math import floor

from django import template

from cetacean_incidents.apps.taxons.models import Taxon

register = template.Library()

@register.simple_tag
def taxon_sort_key(taxon, interleaved=False):
    '''\
    Include a key that can be sorted lexicographically. By default, sorts by
    descending rank, then by name; i.e. a breadth-first traversal of the tree,
    same as the Taxon model's default sort-order. If 'interleaved' is True, will
    sort like a depth-first traversal of the taxon tree, sorted by name within
    the subtaxa of a taxon. Null taxa (which means 'unknown taxon') sort
    before everything else.
    
    Note that these keys aren't guranteed to be stable with the additon of new
    taxa.
    '''
    
    if interleaved:
        return depth_first_sort_key(taxon)
        
    else:
        if taxon is None:
            adjusted_rank = 99
            name = ''
        else:
            # the +50 is to make negative ranks positive.
            adjusted_rank = taxon.rank + 50
            name = taxon.name
        # note that %f will insert a 0 before the decimal point
        return '%02d%.20f %s' % (floor(adjusted_rank), (adjusted_rank) % 1, name)

def _queryset_sort_keys(queryset):
    keys = {}
    i = 1
    for o in queryset:
        keys[o] = i
        i += 1
    
    return keys

def depth_first_sort_key(taxon):
    # assumes no more than 100 subtaxa of any taxon
    
    if taxon is None:
        return '%02d.' % 0
    
    if taxon.supertaxon is None:
        # this is a root node
        root_keys = _queryset_sort_keys(Taxon.objects.filter(supertaxon__isnull=True))
        return '%02d.' % root_keys[taxon]
    
    # the sortkey will be the supertaxon's sort key with two digits appended
    prefix = depth_first_sort_key(taxon.supertaxon)
    suffix = _queryset_sort_keys(taxon.supertaxon.subtaxa.all())[taxon]
    
    return '%s%02d' % (prefix, suffix)
    
