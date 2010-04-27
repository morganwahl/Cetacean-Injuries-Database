from models import Taxon

'''Utility functions for the taxon model.'''

def probable_taxon(observations):
    '''\
    Given a queryset of Observations, finds the Taxon that is a supertaxon of 
    all the Taxa mentioned. If no such Taxon exists, returns None.
    '''

    # TODO fancier algorithm

    # note that values_list returns taxon IDs or Nones
    taxon_ids = observations.values_list('taxon', flat=True)
    # remove Nones
    taxon_ids = filter( lambda x: not x is None, taxon_ids )
    if len(taxon_ids) == 0:
        return None
    
    taxon_ids = set(taxon_ids)
    taxa = set()
    for id in taxon_ids:
        taxa.add(Taxon.objects.get(id=id))
        
    # remove taxa that are ancestors of other taxa in the set
    for taxon in frozenset(taxa):
        # be sure a taxon's ancestors property doesn't include itself!
        taxa -= set(taxon.ancestors)

    if len(taxa) == 1:
        return taxa.pop()
    
    supertaxa = []
    depth = float('inf')
    for taxon in taxa:
        ancestors = taxon.ancestors
        depth = min(depth, len(ancestors))
        supertaxa.append(ancestors)
    
    candidate = None
    for i in range(depth + 1):
        taxa_at_this_depth = set(map(lambda x: x[i], supertaxa)) 
        if len(taxa_at_this_depth) > 1:
            break
        candidate = taxa_at_this_depth.pop()
    
    return candidate
